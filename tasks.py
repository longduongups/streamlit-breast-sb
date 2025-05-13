# Add-on tasks
# ------------
# Author: Victor Jockin
# Last update: 27/04/2025

import bpy

from abc         import ABC, abstractmethod
from collections import deque
from typing      import Callable, Any

from .addon            import AddonContext, AddonSettings, AddonStorage
from .utils._3d_utils  import *
from .utils.stat_utils import *
from mathutils.geometry import convex_hull_2d
from mathutils import Vector
from datetime import datetime
from .db_poitrine import insert_breast_measurement
from .db_supabase import send_to_supabase


# ******************************************************************************************
#   ABSTRACT CLASS REPRESENTING A TASK
# ******************************************************************************************


class TaskDoneException(Exception) :
  # constructor
  def __init__(self, _task: '_Task') :
    super().__init__(f"Task {_task.__class__.__name__} Done")
    self.task = _task

class _Task(ABC) :
  # constructor
  def __init__(self) :
    self.__step : int = 0

  # gives the current step of the task
  def get_step(self) -> int :
    return self.__step

  # runs the next step of the task
  def next_step(self) -> float | None :
    self.__step += 1
    try :
      self._run_step()
    except TaskDoneException as tde :
      if tde.task is self :
        return None
      raise tde
    return AddonSettings.perfs.STEP_TIME_INTERVAL

  @abstractmethod # contains instructions for a step
  def _run_step(self) -> None :
    pass

  # stops task execution
  def _finalize(self) -> None :
    raise TaskDoneException(self)

# ******************************************************************************************
#   TASK MANAGER
# ******************************************************************************************

class TaskManager :
  # constructor
  def __init__(self) :
    self.__tasks        : deque[tuple[Callable[..., _Task], tuple, dict]] = deque()
    self.__current_task : _Task | None                                    = None
    self.__is_started   : bool                                            = False
    self.__on_finished  : Callable[[], None] | None                       = None

  # indicates whether the manager has started
  def is_started(self) -> bool :
    return self.__is_started

  # adds a task to the manager
  def add_task(self, _task_cls: type[_Task], *_args: Any, **_kwargs: Any) -> None :
    self.__tasks.append((_task_cls, _args, _kwargs))

  # defines the behavior of the task manager when all tasks have been executed
  def set_on_finished(self, _callback: Callable[[], None]) -> None :
    self.__on_finished = _callback

  # starts the manager
  def start(self) -> None :
    if not self.__is_started :
      self.__is_started = True
      self.__launch_next()
  
  # launches the next task in the manager
  def __launch_next(self) -> None :
    if self.__tasks :
      task_cls, args, kwargs = self.__tasks.popleft()
      self.__current_task = task_cls(*args, **kwargs)
      bpy.app.timers.register(self.__run_step)
    else :
      self.__is_started = False
      self.__current_task = None
      if self.__on_finished :
        self.__on_finished()
  
  # runs a step of the current task
  def __run_step(self) -> None :
    task_result = self.__current_task.next_step()
    if task_result is None :
      self.__current_task = None
      return self.__launch_next() or None
    return task_result

  # resets the task manager
  def reset(self) :
    self.__tasks.clear()
    self.__current_task = None
    self.__is_started = False

# ******************************************************************************************
#   TASK 1: VERTICAL OBJECT SLICING
# ******************************************************************************************

class VerticalObjectSlicingTask(_Task) :
  def __init__(self) :
    super().__init__()
    # getting object end coordinates on z
    object_bbox_ec = BoundingBox(AddonContext.get_object()).end_coordinates
    object_min_z = object_bbox_ec.min.z
    object_max_z = object_bbox_ec.max.z
    # initializing variables
    self.position_on_axis = object_min_z + (AddonSettings.analysis_params.SECTION_HEIGHT/2)
    self.max_position     = object_max_z
    self.object_slices    = []

  def _run_step(self) :
    if self.position_on_axis >= self.max_position :
      # storing object slices
      AddonStorage.set('OBJECT_SLICES', self.object_slices)
      self._finalize()
    # getting the object slice
    slice = get_object_slice(
      AddonContext.get_object(),
      Direction.Z,
      self.position_on_axis,
      AddonSettings.analysis_params.SECTION_HEIGHT
    )
    # storing the object islands
    self.object_slices += get_object_islands(slice)
    # removing the slice
    bpy.data.objects.remove(slice, do_unlink=True)
    self.position_on_axis += AddonSettings.analysis_params.SECTION_HEIGHT

# ******************************************************************************************
#   TASK 2: OBJECT CENTER CALCULATION TASK
# ******************************************************************************************

class Object2DCenterCalculationTask(_Task) :
  def __init__(self) :
    super().__init__()
    # creating the cutting cylinder
    bpy.ops.mesh.primitive_cylinder_add(
      depth    = AddonSettings.analysis_params.SECTION_HEIGHT + 0.01,
      vertices = AddonSettings.analysis_params.CUTTING_CYLINDER_VERTICES
    )
    # initializing variables
    self.cutting_cylinder        = bpy.context.object
    self.object_slices           = AddonStorage.get('OBJECT_SLICES')
    self.ref_slice_index         = 0
    self.cur_slice_index         = 0
    self.intersection_count      = 0
    self.scores                  = (0, 0)
    self.best_intersection_count = 0
    self.best_scores             = (0, 0)
    self.best_center             = Vector((0, 0))
    # applying object location before processing
    bpy.context.view_layer.objects.active = AddonContext.get_object()
    AddonContext.get_object().select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)

  @property # gives access to the reference slice
  def ref_slice(self) :
    return self.object_slices[self.ref_slice_index]

  @property # gives access to the current slice
  def cur_slice(self) :
    return self.object_slices[self.cur_slice_index]

  # moves on to the next reference slice
  def next_ref_slice(self) :
    self.intersection_count = 0
    self.scores = (0, 0)
    self.ref_slice_index += 1
    self.cur_slice_index = 0

  def _run_step(self) :
    if (
      self.cur_slice_index < len(self.object_slices)
    ) and ((
        self.cur_slice_index == self.ref_slice_index
      ) or not (
        are_bounding_cylinders_intersecting(self.ref_slice, self.cur_slice)
    )) :
      # skipping a step if slices are identical or do not overlap
      self.cur_slice_index += 1
    if self.cur_slice_index >= len(self.object_slices) :
      # updating the best score if necessary
      center = BoundingCylinder(self.ref_slice).center.world.xy
      if self.best_scores[0] < self.scores[0] :
        self.best_scores = (self.scores[0], self.best_scores[1])
        self.best_center.x = center.x
      if self.best_scores[1] < self.scores[1] :
        self.best_scores = (self.best_scores[0], self.scores[1])
        self.best_center.y = center.y
      self.best_intersection_count = max(self.best_intersection_count, self.intersection_count)
      # moving on to the next reference slice
      self.next_ref_slice()
    if (
      (len(self.object_slices) - self.cur_slice_index) <= self.best_scores[0] - self.scores[0]
    ) and (
      (len(self.object_slices) - self.cur_slice_index) <= self.best_scores[1] - self.scores[1]
    ) or (
      (len(self.object_slices) - self.cur_slice_index) < self.best_intersection_count - self.intersection_count
    ) :
      # moving on to the next reference slice when a better score cannot be reached
      self.next_ref_slice()
    if self.ref_slice_index >= len(self.object_slices) :
      # redefining the object's center
      AddonContext.get_object().location -= Vector((self.best_center.x, self.best_center.y, 0.0))
      bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
      # applying object location
      bpy.context.view_layer.objects.active = AddonContext.get_object()
      AddonContext.get_object().select_set(True)
      bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
      # removing the cutting cylinder
      bpy.data.objects.remove(self.cutting_cylinder, do_unlink=True)
      # removing object slices
      for s in self.object_slices :
        bpy.data.objects.remove(s, do_unlink=True)
      self._finalize()
    # getting bounding cylinders
    ref_slice_bcyl = BoundingCylinder(self.ref_slice)
    cur_slice_bcyl = BoundingCylinder(self.cur_slice)
    # adjusting the cutting cylinder
    self.cutting_cylinder.scale      = (1, 1, 1)
    self.cutting_cylinder.scale.x    = ref_slice_bcyl.radius
    self.cutting_cylinder.scale.y    = ref_slice_bcyl.radius
    self.cutting_cylinder.location   = ref_slice_bcyl.center.world
    self.cutting_cylinder.location.z = cur_slice_bcyl.center.world.z
    # getting the intersection between the current slice and the cutting cylinder
    intersection = get_object_intersection(self.cur_slice, self.cutting_cylinder)
    if intersection is not None :
      self.intersection_count += 1
      # getting the intersection bounding cylinder
      intersection_bcyl = BoundingCylinder(intersection)
      # updating scores
      self.scores = (
        self.scores[0] + calc_similarity_coefficient(
          intersection_bcyl.center.world.x,
          ref_slice_bcyl.center.world.x,
          ref_slice_bcyl.radius,
          AddonSettings.analysis_params.SIMILARITY_COEFFICIENT_WEIGHT
        ),
        self.scores[1] + calc_similarity_coefficient(
          intersection_bcyl.center.world.y,
          ref_slice_bcyl.center.world.y,
          ref_slice_bcyl.radius,
          AddonSettings.analysis_params.SIMILARITY_COEFFICIENT_WEIGHT
        ),
      )
      # removing the intersection
      bpy.data.objects.remove(intersection, do_unlink=True)
    # moving on to the next slice
    self.cur_slice_index += 1

# ******************************************************************************************
#   TASK 3: LARGEST SYMMETRICAL ZONE SEARCH
# ******************************************************************************************

class LargestSymmetricalZoneSearchTask(_Task) :
  def __init__(self) :
    super().__init__()
     # getting object end coordinates on z
    object_bbox = BoundingBox(AddonContext.get_object())
    # creating the cutting cylinder
    bpy.ops.mesh.primitive_cylinder_add(
      depth    = object_bbox.dimensions.z + 0.0001,
      location = (0,0,object_bbox.center.z)
    )
    # initializing variables
    self.cutting_cylinder         = bpy.context.active_object
    self.largest_symmetrical_zone = None
    self.cutting_cylinder_radius  = BoundingCylinder(AddonContext.get_object()).radius
    self.z_rot                    = 0

  def _run_step(self) :
    if self.cutting_cylinder_radius <= 0 :
      self._finalize()
    if self.z_rot == 180 :
      # repositioning the cut zone
      self.largest_symmetrical_zone.rotation_euler.z = math.radians(-180)
      bpy.context.view_layer.objects.active = self.largest_symmetrical_zone
      self.largest_symmetrical_zone.select_set(True)
      bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
      # storing the largest symmetrical zone and its radius
      AddonStorage.set('LARGEST_SYMMETRICAL_ZONE', self.largest_symmetrical_zone)
      AddonStorage.set('LARGEST_SYMMETRICAL_ZONE_RADIUS', self.cutting_cylinder_radius)
      # removing the cutting cylinder
      bpy.data.objects.remove(self.cutting_cylinder, do_unlink=True)
      self._finalize()
    if self.largest_symmetrical_zone is None :
      # adjusting the cutting cylinder radius
      self.cutting_cylinder.scale.x = self.cutting_cylinder_radius
      self.cutting_cylinder.scale.y = self.cutting_cylinder_radius
      # copying the original object
      self.largest_symmetrical_zone      = AddonContext.get_object().copy()
      self.largest_symmetrical_zone.data = AddonContext.get_object().data.copy()
      bpy.context.collection.objects.link(self.largest_symmetrical_zone)
      # cutting out the area
      boolean_modifier = self.largest_symmetrical_zone.modifiers.new(name='cutter', type='BOOLEAN')
      boolean_modifier.operation = 'INTERSECT'
      boolean_modifier.object = self.cutting_cylinder
      boolean_modifier.solver = 'FAST'
      bpy.context.view_layer.objects.active = self.largest_symmetrical_zone
      bpy.ops.object.modifier_apply(modifier=boolean_modifier.name)
      # reducing the number of vertices in the cut object
      reduce_object_vertices(
        self.largest_symmetrical_zone,
        AddonSettings.analysis_params.MAX_VERTICES_FOR_FAST_PROCESSING
      )
    else :
      # getting the object center
      lsz_bbox_center = BoundingBox(self.largest_symmetrical_zone).center
      if (
        abs(lsz_bbox_center.x) > AddonSettings.analysis_params.COORDINATE_TOLERANCE
      ) or (
        abs(lsz_bbox_center.y) > AddonSettings.analysis_params.COORDINATE_TOLERANCE
      ) :
        # moving on to the next zone
        bpy.data.objects.remove(self.largest_symmetrical_zone, do_unlink=True)
        self.largest_symmetrical_zone = None
        self.cutting_cylinder_radius -= 0.01
        self.z_rot = 0
      else :
        # rotating the object
        self.largest_symmetrical_zone.rotation_euler.z += math.radians(1)
        bpy.context.view_layer.objects.active = self.largest_symmetrical_zone
        self.largest_symmetrical_zone.select_set(True)
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
        self.z_rot += 1

# ******************************************************************************************
#   TASK 4: SYMMETRICAL ZONE REDUCTION
# ******************************************************************************************

class SymmetricalZoneVerticalReductionTask(_Task) :
  def __init__(self) :
    super().__init__()
    # creating the reference cylinder
    bpy.ops.mesh.primitive_cylinder_add(
      radius = AddonStorage.get('LARGEST_SYMMETRICAL_ZONE_RADIUS'),
      depth  = AddonSettings.analysis_params.SECTION_HEIGHT
    )
    # getting object end coordinates on z
    object_bbox_ec = BoundingBox(AddonContext.get_object()).end_coordinates
    object_min_z = object_bbox_ec.min.z
    object_max_z = object_bbox_ec.max.z
    # initializing variables
    self.reference_cylinder       = bpy.context.active_object
    self.largest_symmetrical_zone = AddonStorage.get('LARGEST_SYMMETRICAL_ZONE')
    self.lsz_slices               = []
    self.position_on_axis         = object_min_z + (AddonSettings.analysis_params.SECTION_HEIGHT/2)
    self.max_position             = object_max_z

  def _run_step(self) :
    if self.position_on_axis >= self.max_position :
      # removing the reference cylinder
      bpy.data.objects.remove(self.reference_cylinder, do_unlink=True)
      # removint the largest symmetrical zone
      bpy.data.objects.remove(self.largest_symmetrical_zone, do_unlink=True)
      # storing slices from the largest symmetrical zone
      AddonStorage.set('LARGEST_SYMMETRICAL_ZONE_SLICES', self.lsz_slices)
      self._finalize()
    # getting the object largest symmetrical zone
    slice = get_object_slice(
      self.largest_symmetrical_zone,
      Direction.Z,
      self.position_on_axis,
      AddonSettings.analysis_params.SECTION_HEIGHT
    )
    # getting bounding boxes
    slice_dimensions   = BoundingBox(slice).dimensions
    ref_cyl_dimensions = BoundingBox(self.reference_cylinder).dimensions
    if ((
        slice_dimensions.x / ref_cyl_dimensions.x
      ) > AddonSettings.analysis_params.CYLINDER_SIMILARITY_THRESHOLD
    ) and ((
        slice_dimensions.y / ref_cyl_dimensions.y
      ) > AddonSettings.analysis_params.CYLINDER_SIMILARITY_THRESHOLD
    ) and ((
        get_object_volume(slice) / get_object_volume(self.reference_cylinder)
      ) > AddonSettings.analysis_params.CYLINDER_SIMILARITY_THRESHOLD
    ) :
      # removing the slice if it is too cylindrical
      bpy.data.objects.remove(slice, do_unlink=True)
    else :
      # reducing the number of vertices in the slice
      reduce_object_vertices(
        slice,
        AddonSettings.analysis_params.MAX_VERTICES_FOR_FAST_PROCESSING
      )
      # storing the slice
      self.lsz_slices.append(slice)
    self.position_on_axis += AddonSettings.analysis_params.SECTION_HEIGHT

# ******************************************************************************************
#   TASK 5: SYMMETRY PLANE ORIENTATION SEARCH
# ******************************************************************************************

class SymmetryPlaneOrientationSearchTask(_Task) :
  def __init__(self) :
    super().__init__()
    self.lsz_slices          = AddonStorage.get('LARGEST_SYMMETRICAL_ZONE_SLICES')
    self.current_slice_index = 0
    self.theta_in_degrees    = 0
    self.angles              = []
    self.best_score          = 0
    self.best_theta          = 0
    # applying object rotation before processing
    bpy.context.view_layer.objects.active = AddonContext.get_object()
    AddonContext.get_object().select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)

  @property # gives access to the current slice
  def current_slice(self) :
    return self.lsz_slices[self.current_slice_index]

  def _run_step(self) :
    if self.theta_in_degrees >= 90 :
      # storing the best angle
      self.angles.append(math.degrees(self.best_theta))
      # removine the current slice
      bpy.data.objects.remove(self.current_slice, do_unlink=True)
      # moving on to the next slice
      self.current_slice_index += 1
      self.theta_in_degrees = -90
      self.best_theta = 0
      self.best_score = 0
    if self.current_slice_index >= len(self.lsz_slices) :
      # removing angles too far from the median
      filtered_angles = [x for x in self.angles if abs(x - calc_median(self.angles)) <= 5]
      # calculating the rotation to be applied to the object
      z_rot = sum(filtered_angles) / len(filtered_angles)
      # applying object rotation
      bpy.context.view_layer.objects.active = AddonContext.get_object()
      AddonContext.get_object().rotation_euler.z = math.radians(z_rot)
      AddonContext.get_object().select_set(True)
      bpy.ops.object.transform_apply(location=True, rotation=True, scale=False)
      # drawing the object's symmetry plane (optional)
      bpy.ops.mesh.primitive_plane_add(
        size     = 2,
        location = (0, 0, 0),
        rotation = (0, math.radians(90), math.radians(90))
      )
      self._finalize()
    # getting projected an mirrored object vertices
    vertices = [self.current_slice.matrix_world @ v.co for v in self.current_slice.data.vertices]
    theta = math.radians(self.theta_in_degrees)
    rotated_vertices, mirrored_vertices = get_projected_and_mirrored_2d_vertices(vertices, theta)
    # analyzing vertices symmetry
    score = 0
    for v in rotated_vertices :
      closest = min(mirrored_vertices, key=lambda m: (v - m).length)
      if (v - closest).length < AddonSettings.analysis_params.DISTANCE_TOLERANCE :
        score += 1
    # updating the best score if necessary
    if score > self.best_score :
      self.best_score = score
      self.best_theta = theta
    # moving on to the next angle
    self.theta_in_degrees += 1

# ******************************************************************************************
#   TASK 6: OBJECT VERTICAL REDUCTION TASK
# ******************************************************************************************

class ObjectVerticalReductionTask(_Task) :
  def __init__(self) :
    super().__init__()
    # getting object end coordinates on z
    object_bbox_ec = BoundingBox(AddonContext.get_object()).end_coordinates
    object_min_z = object_bbox_ec.min.z
    object_max_z = object_bbox_ec.max.z
    # initializing variables
    self.position_on_axis = object_min_z + (AddonSettings.analysis_params.SECTION_HEIGHT/2)
    self.max_position     = object_max_z
    self.results          = []

  def _run_step(self) :
    if self.position_on_axis >= self.max_position :
      self._finalize()
    slice = get_object_slice(
      AddonContext.get_object(),
      Direction.Z,
      self.position_on_axis,
      AddonSettings.analysis_params.SECTION_HEIGHT
    )
    slice_volume = get_object_volume(slice)
    if self.results :
      d = slice_volume - self.results[-1]
      s = '+' if d >= 0 else ''
      print(f"  {s}{d}")
    print(f"SLICE VOLUME:  {slice_volume}")
    self.results.append(slice_volume)
    bpy.context.view_layer.objects.active = AddonContext.get_object()
    self.position_on_axis += AddonSettings.analysis_params.SECTION_HEIGHT

from mathutils import Vector
import math

class BreastMeasurementTask(_Task):
    def __init__(self):
        super().__init__()
        self.object = AddonContext.get_object()
        self.object_bbox = BoundingBox(self.object)
        self.section_height = AddonSettings.analysis_params.CHEST_ISOLATION_SLICE_HEIGHT
        self.min_z = self.object_bbox.end_coordinates.min.z
        self.max_z = self.object_bbox.end_coordinates.max.z
        self.position_on_axis = self.min_z + (self.section_height / 2)
        self.detecting = False
        self.z_start = None
        self.z_end = None
        self.breast_slices_info = []  # Stores (z, x_min) of slices with detected breasts

    def _run_step(self):
        if self.position_on_axis >= self.max_z or (self.z_start and self.z_end):
            if self.z_start and self.z_end:
                z_bottom = self.z_start - self.section_height
                z_top = self.z_end + self.section_height
                height_cm = (z_top - z_bottom) * 100
                AddonStorage.set('BREAST_HEIGHT', height_cm)
                print(f"Height: {height_cm:.3f} cm")

                if self.breast_slices_info:
                    best_z, _ = min(self.breast_slices_info, key=lambda info: info[1])  # Most forward slice

                    best_slice_obj = get_object_slice(self.object, Direction.Z, best_z, self.section_height)
                    if best_slice_obj:
                        vertices = [best_slice_obj.matrix_world @ v.co for v in best_slice_obj.data.vertices]
                        if vertices:
                            min_y = min(v.y for v in vertices)
                            max_y = max(v.y for v in vertices)
                            width_left = abs(min_y) - 0.01
                            width_right = abs(max_y) - 0.01
                            AddonStorage.set('WIDTH_LEFT', width_left * 100)
                            AddonStorage.set('WIDTH_RIGHT', width_right * 100)

                            print("\n--- Forward Slice Measurement ---")
                            print(f"Z: {best_z:.3f} m")
                            print(f"Left Width: {width_left * 100:.3f} cm")
                            print(f"Right Width: {width_right * 100:.3f} cm")
                            print("--- End ---\n")
                        bpy.data.objects.remove(best_slice_obj, do_unlink=True)

                    self._create_slice(self.z_start, "Breast_Slice_Bottom", (0, 1, 0, 1))
                    self._create_slice(self.z_end, "Breast_Slice_Top", (1, 0, 0, 1))
                    self._create_slice(best_z, "Breast_Slice_Forward", (0.2, 0.6, 1.0, 1))

                    self._find_band_slice(best_z)
                    self._find_extreme_breast_points(z_bottom, z_top)
                    self._breast_center(z_top)
                    self.compute_breast_volume_sym_diff(z_bottom, z_top, AddonStorage.get("Z_BAND"))

                    bust = self._measure_circumference_at_z(best_z)
                    if bust:
                        AddonStorage.set("BUST", bust)
                        print(f"Bust Circumference: {bust * 100:.3f} cm")
            timestamp = datetime.now().isoformat()
            height = AddonStorage.get("BREAST_HEIGHT")
            w_left = AddonStorage.get("WIDTH_LEFT")
            w_right = AddonStorage.get("WIDTH_RIGHT")
            band = AddonStorage.get("BAND")*100
            bust = AddonStorage.get("BUST")*100
            volume = AddonStorage.get("BREAST_VOLUME_SYM_DIFF") * 1_000_000  #  cm³
            h_type = AddonStorage.get("BREAST_TYPE_HORIZONTAL")
            v_type = AddonStorage.get("BREAST_TYPE_VERTICAL")

            insert_breast_measurement(height, w_left, w_right, band, bust, volume, h_type, v_type)
            send_to_supabase(height, w_left, w_right, band, bust, volume, h_type, v_type)
            self._finalize()
            return

        slice = get_object_slice(self.object, Direction.Z, self.position_on_axis, self.section_height)
        if slice is None:
            self.position_on_axis += self.section_height
            return

        has_breasts, x_min = self._analyze_slice(slice)
        if has_breasts:
            if not self.detecting:
                self.z_start = self.position_on_axis
                self.detecting = True
            self.breast_slices_info.append((self.position_on_axis, x_min))
        else:
            if self.detecting and self.z_end is None:
                self.z_end = self.position_on_axis
                self.detecting = False

        bpy.data.objects.remove(slice, do_unlink=True)
        self.position_on_axis += self.section_height

    def _analyze_slice(self, slice_obj):
        vertices = [slice_obj.matrix_world @ v.co for v in slice_obj.data.vertices]
        if not vertices or len(vertices) < 3:
            return False, None

        left_vertices = [v for v in vertices if v.y < -0.01]
        right_vertices = [v for v in vertices if v.y > 0.01]
        center_vertices = [v for v in vertices if abs(v.y) <= 0.01]

        if not left_vertices or not right_vertices or not center_vertices:
            return False, None

        best_left = min(left_vertices, key=lambda v: v.x)
        best_right = min(right_vertices, key=lambda v: v.x)
        best_center = min(center_vertices, key=lambda v: v.x)

        if (best_center.x - best_left.x) < 0.003 or (best_center.x - best_right.x) < 0.003:
            return False, None

        dx = best_left.x - best_right.x
        dy = best_left.y - best_right.y
        distance = math.sqrt(dx**2 + dy**2)

        if distance < 0.04:
            return False, None

        x_min = min(best_left.x, best_right.x)
        return True, x_min

    def _create_slice(self, z, name, color):
        slice_obj = get_object_slice(self.object, Direction.Z, z, self.section_height)
        if slice_obj:
            slice_obj.name = name
            self._assign_material(slice_obj, color)

    def _assign_material(self, obj, color):
        mat = bpy.data.materials.new(name="Slice_Material")
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs['Base Color'].default_value = color

        if len(obj.data.materials) == 0:
            obj.data.materials.append(mat)
        else:
            obj.data.materials[0] = mat
    def _find_band_slice(self, best_z):
        print("\n--- Searching for the band under the bust ---")
        current_z = self.min_z + (self.section_height / 2)
        previous_info = None
        band_slice_info = None
        found_transition = False

        while current_z < best_z:
            slice = get_object_slice(
                self.object,
                Direction.Z,
                current_z,
                self.section_height
            )

            if not slice:
                current_z += self.section_height
                continue

            islands = get_object_islands(slice)
            island_count = len(islands)
            print(f"Z: {current_z:.3f} m → {island_count} island(s)")

            if previous_info:
                prev_z, prev_slice, prev_islands = previous_info
                prev_count = len(prev_islands)

                if prev_count > 2 and island_count == 2:
                    band_slice_info = previous_info
                    found_transition = True
                    break
            
            previous_info = (current_z, slice, islands)
            current_z += self.section_height

        if not found_transition:
            if self.z_start:
                fallback_z = self.z_start - 2 * self.section_height
                print(f"No transition detected → fallback to Z = {fallback_z:.3f}")
                slice = get_object_slice(self.object, Direction.Z, fallback_z, self.section_height)
                if slice:
                    islands = get_object_islands(slice)
                    band_slice_info = (fallback_z, slice, islands)

        if not band_slice_info:
            print("No band detected.")
            return

        z_band, slice_obj, islands = band_slice_info

        # If multiple islands, keep only the largest
        if len(islands) > 1:
            print("Multiple islands found → keeping only the largest.")
            try:
                largest = max(islands, key=lambda obj: get_object_volume(obj))
                for isl in islands:
                    if isl != largest:
                        bpy.data.objects.remove(isl, do_unlink=True)
                slice_obj = largest
            except Exception as e:
                print("Error while identifying the largest island:", e)
                return

        slice_obj.name = "Breast_Slice_Band"
        self._assign_material(slice_obj, (1.0, 0.5, 0.0, 1))

        verts = [slice_obj.matrix_world @ v.co for v in slice_obj.data.vertices]


        points_2d = [(v.x, v.y) for v in verts]
        indices = convex_hull_2d(points_2d)
        if indices and len(indices) >= 3:
            hull = [Vector(points_2d[i]) for i in indices]
            perimeter = sum((hull[i] - hull[(i + 1) % len(hull)]).length for i in range(len(hull)))
            AddonStorage.set("BAND", perimeter)
            print(f"Underbust (band) circumference: {perimeter * 100:.3f} cm")
        else:
            print("Invalid convex hull for band.")

        AddonStorage.set('Z_BAND', z_band)
        print(f"Band detected at Z = {z_band:.3f} m.")


    def _create_marker(self, name, location, color):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.01, location=location)
        obj = bpy.context.object
        obj.name = name

        mat = bpy.data.materials.new(name=f"{name}_Mat")
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs['Base Color'].default_value = color

        obj.data.materials.append(mat)

    def _create_vector_line(self, name, p1, p2, color):
        mesh = bpy.data.meshes.new(name)
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(obj)

        mesh.from_pydata([p1, p2], [(0, 1)], [])
        mesh.update()

        mat = bpy.data.materials.new(name=f"{name}_Mat")
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = color
        obj.data.materials.append(mat)

        obj.show_in_front = True  

    


    def _breast_center(self, z_top):
        
        def vector_analysis(name, vector, is_left):
            v_norm = vector.normalized()

            # --- HORIZONTAL ANGLE (XY plane, relative to -X) ---
            xy_proj = Vector((v_norm.x, v_norm.y)).normalized()
            angle_horizontal = math.degrees(math.atan2(xy_proj.y, -xy_proj.x))  # -X is forward

            if is_left:
                if angle_horizontal < 0:
                    dir_h = "outward"
                elif angle_horizontal > 0:
                    dir_h = "inward"
                else:
                    dir_h = "frontal"
            else:
                if angle_horizontal > 0:
                    dir_h = "outward"
                elif angle_horizontal < 0:
                    dir_h = "inward"
                else:
                    dir_h = "frontal"

            # VERTICAL ANGLE
            angle_vertical = math.degrees(math.asin(v_norm.z))
            dir_v = "downward" if angle_vertical < 0 else "upward" if angle_vertical > 0 else "horizontal"

            print(f"{name} - Horizontal: {abs(angle_horizontal):.1f}° → {dir_h}")
            print(f"{name} - Vertical:   {abs(angle_vertical):.1f}° → {dir_v}")

        def classify_breast_posture(vec_left: Vector, vec_right: Vector) -> dict:

              def get_angles(vector: Vector) -> tuple[float, float]:
                  v_norm = vector.normalized()
                  xy_proj = Vector((v_norm.x, v_norm.y)).normalized()
                  angle_horizontal = abs(math.degrees(math.atan2(xy_proj.y, -xy_proj.x)))
                  angle_vertical = abs(math.degrees(math.asin(v_norm.z)))
                  return angle_horizontal, angle_vertical

              angle_h_left, angle_v_left = get_angles(vec_left)
              angle_h_right, angle_v_right = get_angles(vec_right)

              max_horizontal = max(angle_h_left, angle_h_right)
              max_vertical = max(angle_v_left, angle_v_right)

              horizontal_type = "exo" if max_horizontal > 15 else "natural"
              vertical_type = "relax" if max_vertical > 15 else "natural"

              return {
                  "max_horizontal_angle": max_horizontal,
                  "horizontal_type": horizontal_type,
                  "max_vertical_angle": max_vertical,
                  "vertical_type": vertical_type
              }

        z_band = AddonStorage.get('Z_BAND')
        z_center = (z_top + z_band) / 2
        print(z_band, z_top, z_center)
        center_point = Vector((0.0, 0.0, z_center))

        print(f"Chest center (middle): {center_point}")
        self._create_marker("Breast_Center_Mid", center_point, (1.0, 1.0, 0.0, 1))

        width_left = AddonStorage.get('WIDTH_LEFT') / 100
        width_right = AddonStorage.get('WIDTH_RIGHT') / 100

        offset = 0.01

        # Compute left and right breast center points
        right_center = center_point + Vector((0.0, (width_right / 2) + offset, 0.0))
        left_center = center_point - Vector((0.0, (width_left / 2) + offset, 0.0))

        print(f"Right breast center: {right_center}")
        print(f"Left breast center: {left_center}")

        self._create_marker("Breast_Center_Right", right_center, (0.0, 0.5, 1.0, 1))
        self._create_marker("Breast_Center_Left", left_center, (1.0, 0.2, 0.2, 1))

        best_left = AddonStorage.get('BEST_LEFT_POINT')
        best_right = AddonStorage.get('BEST_RIGHT_POINT')

        vec_left = best_left - left_center
        vec_right = best_right - right_center

        print(f"Left vector: {vec_left}")
        print(f"Right vector: {vec_right}")

        self._create_vector_line("Vector_Left", left_center, best_left, (1, 0.4, 0.4, 1))
        self._create_vector_line("Vector_Right", right_center, best_right, (0.4, 0.6, 1, 1))
        vector_analysis("Left", vec_left, True)
        vector_analysis("Right", vec_right, False)
        result = classify_breast_posture(vec_left, vec_right)

        print(f"Horizontal max angle: {result['max_horizontal_angle']:.1f}° → {result['horizontal_type']}")
        print(f"Vertical max angle:   {result['max_vertical_angle']:.1f}° → {result['vertical_type']}")
        AddonStorage.set("BREAST_TYPE_HORIZONTAL", result["horizontal_type"])
        AddonStorage.set("BREAST_TYPE_VERTICAL", result["vertical_type"])


    def _find_extreme_breast_points(self, z_bottom, z_top):
        best_left = None
        best_right = None
        min_x_left = float('inf')
        min_x_right = float('inf')

        z = z_bottom
        while z <= z_top:
            slice = get_object_slice(self.object, Direction.Z, z, self.section_height)
            if not slice:
                z += self.section_height
                continue

            vertices = [slice.matrix_world @ v.co for v in slice.data.vertices]
            for v in vertices:
                if v.y < 0 and v.x < min_x_left:
                    min_x_left = v.x
                    best_left = v
                elif v.y > 0 and v.x < min_x_right:
                    min_x_right = v.x
                    best_right = v

            bpy.data.objects.remove(slice, do_unlink=True)
            z += self.section_height

        if best_left:
            AddonStorage.set('BEST_LEFT_POINT', best_left)
            print(f"Leftmost point found: {best_left}")
        else:
            print("No left point found.")

        if best_right:
            AddonStorage.set('BEST_RIGHT_POINT', best_right)
            print(f"Rightmost point found: {best_right}")
        else:
            print("No right point found.")

    def _measure_circumference_at_z(self, z):
        slice = get_object_slice(
            self.object,
            Direction.Z,
            z,
            self.section_height
        )

        if not slice:
            print(f"Aucune slice trouvée à Z = {z:.3f}")
            return None

        verts = [slice.matrix_world @ v.co for v in slice.data.vertices]
        if not verts:
            bpy.data.objects.remove(slice, do_unlink=True)
            print("Slice vide.")
            return None

        points_2d = [(v.x, v.y) for v in verts]
        indices = convex_hull_2d(points_2d)
        if not indices or len(indices) < 3:
            bpy.data.objects.remove(slice, do_unlink=True)
            print("Convex hull invalide.")
            return None

        hull_points = [Vector(points_2d[i]) for i in indices]

        perimeter = sum(
            (hull_points[i] - hull_points[(i + 1) % len(hull_points)]).length
            for i in range(len(hull_points))
        )

        bpy.data.objects.remove(slice, do_unlink=True)
        return perimeter

    def _create_vertical_slice_at_x(self, x_pos: float, name: str, color=(1, 1, 0, 1), thickness=0.002):
        # Create a thin cube aligned on the YZ plane at x = x_pos
        bpy.ops.mesh.primitive_cube_add(size=1)
        slice_obj = bpy.context.object
        slice_obj.name = name

        bbox = self.object_bbox
        dimensions = bbox.dimensions
        center_y = bbox.center.y
        center_z = bbox.center.z

        slice_obj.scale = (thickness / 2, dimensions.y / 2, dimensions.z / 2)
        slice_obj.location = (x_pos, center_y, center_z)

        self._assign_material(slice_obj, color)

    def compute_breast_volume_sym_diff(self, z_bottom, z_top, z_band):
        def get_front_area(slice_obj, x_cutoff):
            verts = [slice_obj.matrix_world @ v.co for v in slice_obj.data.vertices]
            front_verts = [v for v in verts if v.x < x_cutoff]
            if len(front_verts) < 3:
                return 0.0
            points_2d = [(v.x, v.y) for v in front_verts]
            indices = convex_hull_2d(points_2d)
            if not indices or len(indices) < 3:
                return 0.0
            hull = [Vector(points_2d[i]) for i in indices]
            return abs(sum(
                (hull[i].x * hull[(i + 1) % len(hull)].y - hull[(i + 1) % len(hull)].x * hull[i].y)
                for i in range(len(hull))
            )) / 2.0

        # Step 1: find x_cutoff from top slice at y ≈ 0
        top_slice = get_object_slice(self.object, Direction.Z, z_top, self.section_height)
        if not top_slice:
            print("Top slice not found.")
            return
        center_verts = [top_slice.matrix_world @ v.co for v in top_slice.data.vertices if abs((top_slice.matrix_world @ v.co).y) < 0.01]
        if not center_verts:
            print("No center vertices found.")
            bpy.data.objects.remove(top_slice, do_unlink=True)
            return
        x_cutoff = min(v.x for v in center_verts) + 0.05
        bpy.data.objects.remove(top_slice, do_unlink=True)
        print(f"x_cutoff (front): {x_cutoff:.4f}")
        self._create_vertical_slice_at_x(x_cutoff, "X_Cutoff_Plane", (1.0, 1.0, 0.0, 1))

        # Step 2: get reference areas
        band_slice = get_object_slice(self.object, Direction.Z, z_band, self.section_height)
        if not band_slice:
            print("Band slice not found.")
            return

        # Supprimer petits îlots, garder le plus grand
        islands = get_object_islands(band_slice)
        if len(islands) > 1:
            print(f"Band slice → {len(islands)} îlots trouvés, suppression des petits.")
            try:
                largest = max(islands, key=lambda obj: get_object_volume(obj))
                for isl in islands:
                    if isl != largest:
                        bpy.data.objects.remove(isl, do_unlink=True)
                band_slice = largest
            except Exception as e:
                print("Erreur pendant le tri des îlots :", e)
                return

        band_area = get_front_area(band_slice, x_cutoff)
        top_area = get_front_area(get_object_slice(self.object, Direction.Z, z_top, self.section_height), x_cutoff)
        print(f"Band area: {band_area:.6f}, Top area: {top_area:.6f}")

        z_center = (z_band + z_top) / 2
        total_volume = 0.0
        z = z_bottom

        while z <= z_top:
            slice_obj = get_object_slice(self.object, Direction.Z, z, self.section_height)
            if not slice_obj:
                z += self.section_height
                continue
            area = get_front_area(slice_obj, x_cutoff)

            if z >= z_center:
                delta = max(area - top_area, 0.0)
            else:
                delta = max(area - band_area, 0.0)

            volume = delta * self.section_height
            total_volume += volume
            bpy.data.objects.remove(slice_obj, do_unlink=True)
            z += self.section_height

        volume_cm3 = total_volume * 1_000_000
        AddonStorage.set("BREAST_VOLUME_SYM_DIFF", total_volume)
        print(f"Estimated breast volume (sym diff, cm³): {volume_cm3:.2f}")


    






    


  