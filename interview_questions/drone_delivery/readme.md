## Problem

A warehouse is represented by a starting point, 0, and end point, target. Along the length of the warehouse, there are `n` stations positioned, represented by the array `stations`. This array is not necessarily sorted.

You are to deliver cargo from the start of the warehouse to the end, and employ the use of drones which are placed at each station. Each drone may travel only a maximum distance represented by `MAX_DRONE_DIST`. If a station is too far for a drone to reach, then you must collect the cargo from the last delivered station, and walk with it to the nearest station ahead.

You are required to caluclate the total number of steps walked to deliver the package.

### Constraints
`MAX_DRONE_DIST` = 10 units

### Inputs
stations: list[int]
target: int
