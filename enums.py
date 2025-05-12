# Enumeration classes
# -------------------
# Author: Victor Jockin
# Last update: 07/04/2025

from enum import Enum

class Direction(Enum) :
  X = 'x'
  Y = 'y'
  Z = 'z'

class PlanFace(Enum) :
  ABOVE = 'ABOVE'
  BELOW = 'BELOW'