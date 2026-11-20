from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from myalignment.render.label_box import LabelBox
from myalignment.render.stagger_config import StaggerConfig


@dataclass(frozen=True, slots=True)
class StaggerResult:
    offsets: dict[str, tuple[float, float]]
    level_map: dict[str, int]
    unresolved: tuple[str, ...] = ()


class Staggerer:
    """입력 순서대로 처음 사용 가능한 레벨에 레이블을 배치한다."""

    @classmethod
    def stagger(cls, boxes: Sequence[LabelBox], config: StaggerConfig) -> StaggerResult:
        ids = [box.label_id for box in boxes]
        if len(set(ids)) != len(ids):
            raise ValueError("label_id values must be unique")
        if not config.is_active:
            return StaggerResult(dict.fromkeys(ids, (0.0, 0.0)), dict.fromkeys(ids, 0))

        placed = []
        offsets = {}
        levels = {}
        unresolved = []
        steps = tuple(config.offset_at_level(level) for level in range(config.max_stagger_count + 1))
        for box in boxes:
            for level, (dx, dy) in enumerate(steps):
                candidate = box.shifted(dx, dy)
                if not any(candidate.intersects(other, padding=config.min_spacing) for other in placed):
                    break
            else:
                unresolved.append(box.label_id)
            placed.append(candidate)
            offsets[box.label_id] = (dx, dy)
            levels[box.label_id] = level
        return StaggerResult(offsets, levels, tuple(unresolved))
