# Tests
# -----
# Author: Victor Jockin
# Last update: 27/04/2025

import bpy
import inspect

from abc import ABC

from .addon import AddonContext
from .tasks import *

# ******************************************************************************************
#   ABSTRACT CLASS REPRESENTING A 3D MANIPULATION TEST
# ******************************************************************************************

class _Test(ABC) :
  def run_tests(self) :
    methods = inspect.getmembers(self, predicate=inspect.ismethod)
    for name, method in methods :
      if name.startswith('test_') :
        method()

# ******************************************************************************************
#   OBJECT CALIBRATION TEST
# ******************************************************************************************

class ObjectCalibrationTest(_Test) :
  def __init__(self) :
    self.tm               = TaskManager()
    self.original_object  = None
    self.theta_in_degrees = 0

  def test_object_calibration(self) :
    self.original_object      = AddonContext.get_object().copy()
    self.original_object.data = AddonContext.get_object().data.copy()
    AddonContext.get_object().rotation_euler.z = math.radians(self.theta_in_degrees)
    self.tm.reset()
    self.tm.add_task(VerticalObjectSlicingTask)
    self.tm.add_task(Object2DCenterCalculationTask)
    self.tm.add_task(LargestSymmetricalZoneSearchTask)
    self.tm.add_task(SymmetricalZoneVerticalReductionTask)
    self.tm.add_task(SymmetryPlaneOrientationSearchTask)
    self.tm.set_on_finished(self.on_test_object_calibration_finished)
    self.tm.start()

  def on_test_object_calibration_finished(self) :
    object_bbox = BoundingBox(AddonContext.get_object())
    print(f"OBJECT BBOX:  [ X: {object_bbox.dimensions.x}, Y: {object_bbox.dimensions.y} ]")
    self.theta_in_degrees += 50
    for o in list(bpy.data.objects) :
      if o != self.original_object :
        bpy.data.objects.remove(o, do_unlink=True)
    object = self.original_object.copy()
    object.data = self.original_object.data.copy()
    bpy.context.collection.objects.link(object)
    if self.theta_in_degrees >= 360 :
      return
    self.test_object_calibration()