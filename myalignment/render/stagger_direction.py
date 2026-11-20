from enum import Enum


class StaggerDirection(Enum):
    UP = "Up"
    DOWN = "Down"
    LEFT = "Left"
    RIGHT = "Right"


class StaggerMethod(Enum):
    NONE = "None"
    DISTANCE = "Distance"
    INCREMENT = "Increment"
