# 3D utilities
# ------------
# Author: Victor Jockin
# Last update: 25/04/2025

import bpy
import bmesh
import math

from mathutils import Matrix, Vector
from typing 	 import Any

from ..enums import Direction, PlanFace

# ******************************************************************************************
#   CLASSES
# ******************************************************************************************

class Interval :
	def __init__(self, _min: Any, _max: Any) :
		self.min = _min
		self.max = _max

class Coordinates :
	def __init__(self, _local_coordinates: Vector, _world_coordinates: Vector) :
		self.local = _local_coordinates
		self.world = _world_coordinates
	
	def __str__(self) :
		return f"COORDINATES: ( LOCAL: {self.local}, WORLD: {self.world} )"

class BoundingBox :
	def __init__(self, _object: bpy.types.Object) :
		x_min = y_min = z_min = float('inf')
		x_max = y_max = z_max = float('-inf')
		for v in _object.data.vertices :
			world_positiions = _object.matrix_world @ v.co
			x_min = min(x_min, world_positiions.x)
			x_max = max(x_max, world_positiions.x)
			y_min = min(y_min, world_positiions.y)
			y_max = max(y_max, world_positiions.y)
			z_min = min(z_min, world_positiions.z)
			z_max = max(z_max, world_positiions.z)
		# attribute initialization
		self.__dimensions 		 = Vector((x_max-x_min, y_max-y_min, z_max-z_min))
		self.__end_coordinates = Interval(Vector((x_min, y_min, z_min)), Vector((x_max, y_max, z_max)))
		self.__center					 = Vector(((x_min+x_max)/2, (y_min+y_max)/2, (z_min+z_max)/2))

	@property
	def dimensions(self) :
		return self.__dimensions

	@property
	def end_coordinates(self) :
		return self.__end_coordinates

	@property
	def center(self) :
		return self.__center

class BoundingCylinder :
	def __init__(self, _object: bpy.types.Object) :
		# retrieving object vertices
		local_vertices = [v.co for v in _object.data.vertices]
		# calculating the object barycenter (the center of the bounding cylinder)
		local_barycenter = sum(local_vertices, Vector()) / len(local_vertices)
		world_barycenter = _object.matrix_world @ local_barycenter
		# calculating the radius of the bounding cylinder
		cylinder_radius = max(
			((_object.matrix_world @ lv) - world_barycenter).length
			for lv in local_vertices
		)
		# attribute initialization
		self.__center = Coordinates(local_barycenter, world_barycenter)
		self.__radius = cylinder_radius

	@property
	def center(self) :
		return self.__center

	@property
	def radius(self) :
		return self.__radius

# ******************************************************************************************
#   OBJECT INFO
# ******************************************************************************************

# gives the dimensions of an object from its bounding box
def get_object_dimensions(_object: bpy.types.Object) -> dict[Direction, float] :
	bounding_box = [_object.matrix_world @ Vector(corner) for corner in _object.bound_box]
	dimensions = dict()
	for i, axis in enumerate(Direction) :
		coordinates = [p[i] for p in bounding_box]
		dimensions[axis.value] = max(coordinates) - min(coordinates)
	return dimensions

# gives the island count of an object
def get_object_island_count(_object: bpy.types.Object) -> int :
	bm = bmesh.new()
	bm.from_mesh(_object.data)
	for v in bm.verts :
		v.tag = False
	island_count = 0
	for v in bm.verts:
		if not v.tag :
			stack = [v]
			while stack :
				v2 = stack.pop()
				if not v2.tag :
					v2.tag = True
					stack.extend([e.other_vert(v2) for e in v2.link_edges if not e.other_vert(v2).tag])
			island_count += 1
	bm.free()
	return island_count

def get_object_islands(_object: bpy.types.Object) -> list[bpy.types.Object] :
	if _object.type != 'MESH' :
		print("not a mesh")
		return []
	# duplicating original object
	base = _object.copy()
	base.data = _object.data.copy()
	bpy.context.collection.objects.link(base)

	bpy.context.view_layer.objects.active = base
	bpy.ops.object.select_all(action='DESELECT')
	base.select_set(True)
	bpy.ops.object.mode_set(mode='EDIT')

	bpy.ops.mesh.select_all(action='SELECT')
	bpy.ops.mesh.separate(type='LOOSE')
	bpy.ops.object.mode_set(mode='OBJECT')

	return [ o for o in bpy.context.selected_objects if o.type == 'MESH' ]

def are_bounding_cylinders_intersecting(
	_object1 : bpy.types.Object,
	_object2 : bpy.types.Object
) :
	object1_bcyl = BoundingCylinder(_object1)
	object2_bcyl = BoundingCylinder(_object2)
	return (
		object1_bcyl.center.world.xy - object2_bcyl.center.world.xy
  ).length <= (
    object1_bcyl.radius + object2_bcyl.radius
  )

def get_projected_and_mirrored_2d_vertices(
	_vertices : list[Vector],
	_theta		: float
) -> tuple[list[Vector], list[Vector]] :
	rot = Matrix.Rotation(_theta, 4, 'Z')
	rot_verts = [rot @ (v.xy.to_3d()) for v in _vertices]
	mir_verts = [Vector((v.x, -v.y, 0)) for v in rot_verts]
	return (rot_verts, mir_verts)

# ******************************************************************************************
#   OBJECT TRANSFORMATION
# ******************************************************************************************

# reduces the number of vertices of the object given as a parameter
def reduce_object_vertices(
	_object	: 						bpy.types.Object,
	_max_vertices_count : int
) -> None :
	object_vertices_count = len(_object.data.vertices)
	if object_vertices_count > _max_vertices_count :
		ratio = _max_vertices_count / object_vertices_count
		modifier = _object.modifiers.new(name="decimate", type='DECIMATE')
		modifier.ratio = ratio
		bpy.ops.object.select_all(action='DESELECT')
		bpy.context.view_layer.objects.active = _object
		_object.select_set(True)
		bpy.ops.object.modifier_apply(modifier=modifier.name)

def orient(
	_object 	 		 : bpy.types.Object,
	_direction 		 : Direction 					| None = Direction.Z,
	_reverse_sense : bool								| None = False
) :
	z_rotation = math.radians(180) if _reverse_sense else 0
	rotations = {
		Direction.X : (0, math.radians(-90), z_rotation),
		Direction.Y : (math.radians(90), 0, z_rotation),
		Direction.Z : (0, 0, z_rotation)
	}
	_object.rotation_euler = rotations.get(_direction)

# ******************************************************************************************
#   CUTTING
# ******************************************************************************************

# cuts off part of an object
def cut_object(
	_object						: bpy.types.Object,
	_direction				: Direction 				| None = Direction.Z,
	_cutting_face 		: PlanFace 					| None = PlanFace.BELOW,
	_position_on_axis	: float							| None = 0.0
) :
	width_axis, height_axis = {
		Direction.X: ("y", "z"),
		Direction.Y: ("x", "z"),
		Direction.Z: ("x", "y")
	}[_direction]
	bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0))
	cutting_plane = bpy.context.object
	orient(cutting_plane, _direction, _cutting_face==PlanFace.ABOVE)
	# resizing the plane according to object dimensions
	object_bounding_box = BoundingBox(_object)
	cutting_plane.scale = (
		getattr(object_bounding_box.dimensions, width_axis) + 1,
		getattr(object_bounding_box.dimensions, height_axis) + 1,
		1
	)
	# positioning the plane on the cutting axis
	setattr(cutting_plane.location, _direction.value, _position_on_axis)
	# setting a boolean modifier for cutting
	boolean_modifier = _object.modifiers.new(name='cutter', type='BOOLEAN')
	boolean_modifier.operation = 'DIFFERENCE'
	boolean_modifier.object = cutting_plane
	boolean_modifier.solver = 'EXACT'
	# applying the boolean modifier
	bpy.context.view_layer.objects.active = _object
	bpy.ops.object.modifier_apply(modifier=boolean_modifier.name)
	# deleting the cutting plane
	bpy.data.objects.remove(cutting_plane)

# gives a slice of an object
def get_object_slice(
	_object						 : bpy.types.Object,
	_slicing_direction : Direction,
	_position_on_axis	 : float | None = 0.0,
	_slice_height			 : float | None = 0.1,
	x:float|None=None,
	y:float|None=None
) -> bpy.types.Object :
	# duplicating the given object
	object 			= _object.copy()
	object.data = _object.data.copy()
	object_bounding_box = BoundingBox(_object)
	bpy.context.collection.objects.link(object)
	# setting a slicer
	bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
	slicer = bpy.context.object
	orient(slicer, _slicing_direction)
	width_axis, height_axis = {
		Direction.X: ("y", "z"),
		Direction.Y: ("x", "z"),
		Direction.Z: ("x", "y")
	}[_slicing_direction]
	if x is not None and y is not None :
		slicer.location.x = x
		slicer.location.y = y
	else :
		setattr(slicer.location, width_axis, getattr(object_bounding_box.center, width_axis))
		setattr(slicer.location, height_axis, getattr(object_bounding_box.center, height_axis))
	x_correction = abs(object_bounding_box.center.x - slicer.location.x) * 2
	y_correction = abs(object_bounding_box.center.y - slicer.location.y) * 2
	slicer.scale = (
		getattr(object_bounding_box.dimensions, width_axis) - x_correction + 0.0001,
		getattr(object_bounding_box.dimensions, height_axis) - y_correction + 0.0001,
		_slice_height
	)
	# positioning the slicer on the slicing axis
	setattr(slicer.location, _slicing_direction.value, _position_on_axis)
	# setting a boolean modifier for slicing
	boolean_modifier = object.modifiers.new(name='slicer', type='BOOLEAN')
	boolean_modifier.operation = 'INTERSECT'
	boolean_modifier.object = slicer
	boolean_modifier.solver = 'FAST'
	# applying the boolean modifier
	bpy.context.view_layer.objects.active = object
	bpy.ops.object.modifier_apply(modifier=boolean_modifier.name)
	# deleting the slicer
	bpy.data.objects.remove(slicer, do_unlink=True)
	return object

def get_object_intersection(
	_object_1: bpy.types.Object,
	_object_2: bpy.types.Object
) -> bpy.types.Object :
	# duplicating original objects
	object_1 = _object_1.copy()
	object_2 = _object_2.copy()
	object_1.data = _object_1.data.copy()
	object_2.data = _object_2.data.copy()
	bpy.context.collection.objects.link(object_1)
	bpy.context.collection.objects.link(object_2)
	# selecting the objects
	bpy.ops.object.select_all(action='DESELECT')
	object_1.select_set(True)
	object_2.select_set(True)
	bpy.context.view_layer.objects.active = object_1
	# setting a boolean modifier for intersection
	boolean_modifier = object_1.modifiers.new(name='intersecter', type='BOOLEAN')
	boolean_modifier.operation = 'INTERSECT'
	boolean_modifier.object = object_2
	boolean_modifier.solver = 'FAST'
	# applying the boolean modifier
	bpy.context.view_layer.objects.active = object_1
	bpy.ops.object.modifier_apply(modifier=boolean_modifier.name)
	# deleting the second object
	bpy.data.objects.remove(object_2, do_unlink=True)
	if not object_1.data.polygons :
		bpy.data.objects.remove(object_1, do_unlink=True)
		return None
	return object_1

# ******************************************************************************************
#   AREA AND VOLUME CALCULATION
# ******************************************************************************************

# gives the volume of the object given as a parameter
def get_object_volume(_object: bpy.types.Object) -> float :
	# source: https://blender.stackexchange.com/questions/63113/is-it-possible-to-calculate-and-display-volume-of-a-mesh-object
	me = _object.data
	bm = bmesh.new()
	bm.from_mesh(me)
	bm.transform(_object.matrix_world)
	bmesh.ops.triangulate(bm, faces=bm.faces)
	volume = 0.0
	for face in bm.faces :
		v1 = face.verts[0].co
		v2 = face.verts[1].co
		v3 = face.verts[2].co
		volume += v1.dot(v2.cross(v3)) / 6
	bm.free()
	return volume