from myalignment.render.stagger_config import StaggerConfig
from myalignment.render.stagger_direction import StaggerDirection, StaggerMethod


class StaggerConfigPresets:
    @staticmethod
    def none() -> StaggerConfig:
        return StaggerConfig()

    @staticmethod
    def up_distance(distance: float = 2.0) -> StaggerConfig:
        return StaggerConfig(method=StaggerMethod.DISTANCE, base_offset=distance)

    @staticmethod
    def up_increment(base: float = 2.0, increment: float = 1.5) -> StaggerConfig:
        return StaggerConfig(method=StaggerMethod.INCREMENT, base_offset=base, increment=increment)

    @staticmethod
    def down_increment(base: float = 2.0, increment: float = 1.5) -> StaggerConfig:
        return StaggerConfig(StaggerMethod.INCREMENT, StaggerDirection.DOWN, base_offset=base, increment=increment)

    @staticmethod
    def right_increment(base: float = 3.0, increment: float = 2.0) -> StaggerConfig:
        return StaggerConfig(
            StaggerMethod.INCREMENT, StaggerDirection.RIGHT, max_stagger_count=4,
            base_offset=base, increment=increment,
        )
