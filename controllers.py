# Add-on controllers
# ------------------
# Author: Victor Jockin
# Last update: 25/04/2025

from .tasks import *
from .db_poitrine import init_breast_table
class BooMainController:
    def doObjectCalibration(self):
        tm = TaskManager()
        tm.add_task(VerticalObjectSlicingTask)
        tm.add_task(Object2DCenterCalculationTask)
        tm.add_task(LargestSymmetricalZoneSearchTask)
        tm.add_task(SymmetricalZoneVerticalReductionTask)
        tm.add_task(SymmetryPlaneOrientationSearchTask)
        tm.add_task(ObjectVerticalReductionTask)
        tm.start()

    def doBreastMeasurement(self):
        init_breast_table()
        tm = TaskManager()
        tm.add_task(BreastMeasurementTask)
        tm.start()

