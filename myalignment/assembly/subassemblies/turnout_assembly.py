from dataclasses import dataclass, field, replace
import math

from myalignment.assembly.codes import LinkCode, PointCode
from myalignment.assembly.link import AssemblyLink
from myalignment.assembly.subassemblies.rail_track import SingleTrack


@dataclass(frozen=True, slots=True)
class TurnoutAssembly(SingleTrack):
    """고정 위치의 본선과 분기선 레일을 표현하는 횡단면.

    branch_offset은 분기선 중심의 부호 있는 횡거다. 실제 분기
    경로는 턴아웃 기하 계산과 3D 렌더러에서 별도로 배치한다.
    """

    name: str = field(default="TurnoutAssembly", init=False)
    branch_offset: float = 2.0

    def __post_init__(self):
        SingleTrack.__post_init__(self)
        if not math.isfinite(self.branch_offset) or abs(self.branch_offset) <= self.gauge:
            raise ValueError("branch_offset must be finite and separate the two track sections")

    def generate_geometry(self, target_mapping=None):
        points, links = SingleTrack.generate_geometry(self, target_mapping)
        branch_codes = {
            PointCode.LEFT_RAIL: PointCode.BRANCH_LEFT_RAIL,
            PointCode.RIGHT_RAIL: PointCode.BRANCH_RIGHT_RAIL,
        }
        branch = {
            point: replace(point, code=branch_codes.get(point.code, point.code), x=point.x + self.branch_offset)
            for point in points
        }
        branch_links = tuple(replace(link, start=branch[link.start], end=branch[link.end]) for link in links)
        outer_main = points[3] if self.branch_offset > 0 else points[2]
        inner_branch = branch[points[2] if self.branch_offset > 0 else points[3]]
        # Only join an actual gap between the two ballast shoulders.
        gap = (inner_branch.x - outer_main.x) * math.copysign(1, self.branch_offset)
        bridge = (AssemblyLink(LinkCode.BALLAST, outer_main, inner_branch),) if gap > 0 else ()
        return points + tuple(branch.values()), links + branch_links + bridge
