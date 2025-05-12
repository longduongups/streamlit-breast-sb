# Add-on user interface
# ---------------------
# Author: Victor Jockin
# Last update: 27/04/2025

from bpy.types import Operator, Panel
from bpy.utils import register_class, unregister_class

from .controllers import *
from .tests       import *

# ******************************************************************************************
#   OPERATORS
# ******************************************************************************************

class CALIBRATE_OBJECT_OPERATOR(Operator) :
  bl_idname = "boo.calibrate_object_operator"
  bl_label  = "Calibrate Object"

  def execute(self, _context) :
    bmc = BooMainController()
    bmc.doObjectCalibration()
    return {'FINISHED'}

class TEST_OBJECT_CALIBRATION_OPERATOR(Operator) :
  bl_idname = "boo.test_object_calibration_operator"
  bl_label  = "Test Object Calibration"

  def execute(self, _context) :
    oct = ObjectCalibrationTest()
    oct.run_tests()
    return {'FINISHED'}
class MEASURE_BREAST_OPERATOR(Operator):
    bl_idname = "boo.measure_breast_operator"
    bl_label = "Mesurer Poitrine"

    def execute(self, _context):
        bmc = BooMainController()
        bmc.doBreastMeasurement()
        return {'FINISHED'}


# ******************************************************************************************
#   PANELS
# ******************************************************************************************

class BOO_PT_MAIN_PANEL(Panel) :
  bl_idname 		 = "BOO_PT_mainpanel"
  bl_label 			 = "Boo (TMP)"
  bl_space_type  = 'VIEW_3D'
  bl_region_type = 'UI'
  bl_category 	 = 'Boo (TMP)'

  def draw(self, _context) :
    row = self.layout.row()
    row.active_default = True
    row.operator('boo.calibrate_object_operator')
    self.layout.operator('boo.test_object_calibration_operator')
    self.layout.operator('boo.measure_breast_operator')



# ******************************************************************************************
#   REGISTRATION / DE-REGISTRATION
# ******************************************************************************************

def register() :
  register_class(CALIBRATE_OBJECT_OPERATOR)
  register_class(TEST_OBJECT_CALIBRATION_OPERATOR)
  register_class(MEASURE_BREAST_OPERATOR) 
  register_class(BOO_PT_MAIN_PANEL)
  

def unregister() :
  unregister_class(CALIBRATE_OBJECT_OPERATOR)
  unregister_class(TEST_OBJECT_CALIBRATION_OPERATOR)
  unregister_class(MEASURE_BREAST_OPERATOR)
  unregister_class(BOO_PT_MAIN_PANEL)
  