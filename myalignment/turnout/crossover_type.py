from enum import Enum

class CrossoverType(Enum):
    SINGLE = 'single'
    DOUBLE = 'double'  # two diagonal connections forming an X
    SCISSORS = 'scissors'  # explicitly unsupported until crossing geometry implemented
