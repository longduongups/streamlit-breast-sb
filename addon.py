# Add-on
# ------
# Author: Victor Jockin
# Last update: 26/04/2025

import bpy

from typing import Any

# ******************************************************************************************
#   ADD-ON CONTEXT
# ******************************************************************************************

class AddonContext :
  # attributes
  __object : bpy.types.Object = None

  @classmethod # gives the object to be analyzed
  def get_object(cls) -> bpy.types.Object | None :
    if cls.__object :
      try :
        bpy.context.scene.objects[cls.__object.name]
      except :
        cls.__object = None
    if not cls.__object :
      objects = bpy.context.scene.objects
      is_mesh = False
      i = 0
      while i < len(objects) and not is_mesh :
        if objects[i].type == 'MESH' :
          cls.__object = objects[i]
          is_mesh = True
        i += 1
    return cls.__object

# ******************************************************************************************
#   ADD-ON SETTINGS
# ******************************************************************************************

class ImmutableMeta(type) :
  def __setattr__(cls, name, value) :
    if name in cls.__dict__ :
      raise AttributeError(f"Cannot modify property: {name} is read-only")
    super().__setattr__(name, value)

class _AddonAnalysisParams(metaclass=ImmutableMeta) :
  COORDINATE_TOLERANCE             = 1e-4
  CUTTING_CYLINDER_VERTICES        = 64
  CYLINDER_SIMILARITY_THRESHOLD    = 0.9
  DISTANCE_TOLERANCE               = 1e-3 * 5
  CHEST_ISOLATION_SLICE_HEIGHT     = 0.002
  MAX_VERTICES_FOR_FAST_PROCESSING = 200
  SECTION_HEIGHT                   = 0.01
  SIMILARITY_COEFFICIENT_WEIGHT    = 20

class _AddonPerfs(metaclass=ImmutableMeta) :
  STEP_TIME_INTERVAL = 0.0

class AddonSettings(metaclass=ImmutableMeta) :
  analysis_params = _AddonAnalysisParams
  perfs           = _AddonPerfs

# ******************************************************************************************
#   ADD-ON STORAGE
# ******************************************************************************************

class AddonStorage :
  # attributes
  __data : dict = dict()

  @classmethod # gives the value associated with the specified key
  def get(cls, _key: str) -> Any :
    return cls.__data.get(_key)
  
  @classmethod # stores the specified value under the given key
  def set(cls, _key: str, _value: Any) -> None :
    cls.__data[_key] = _value



