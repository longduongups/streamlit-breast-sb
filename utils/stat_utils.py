# Statistics utilities
# --------------------
# Author: Victor Jockin
# Last update: 27/04/2025

# calculates the median of a list
def calc_median(_l: list) -> float :
  sorted_list = sorted(_l)
  n = len(sorted_list)
  if n % 2 == 1 :
    median = sorted_list[n // 2]
  else :
    median = (sorted_list[n // 2 - 1] + sorted_list[n // 2]) / 2
  return median

# calculates the similarity coefficient between two given values
def calc_similarity_coefficient(
  _value1 : float,
  _value2 : float,
  _range  : float,
  _weight : float | None = 1
) -> float :
  return max(0, 1 - abs(_value1 - _value2) / _range) ** _weight