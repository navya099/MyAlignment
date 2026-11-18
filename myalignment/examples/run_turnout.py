# 철도 선형 생성 (체이닝 및 .build() 정상 작동)
from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.turnout.turnout import Turnout
from myalignment.turnout.type import TurnoutType, TurnoutSide

rail = (
    AlignmentBuilder("본선")
    .with_pi_coords([(0, 0), (500, 0), (1000, 200)])
    .with_radii([None, 800, None])
    .as_rail_alignment(gauge=1.435)   # 설정 메서드 (return self)
    .build()                        # 최종 빌드
)

# 턴아웃 생성 (분기 선형)
turnout_type = TurnoutType(name="F12", frog_number=12, lead_length=30, radius=373)
turnout = Turnout(
    name="5141",
    turnout_type=turnout_type,
    source_alignment_name="본선",
    branch_alignment_name="분기선",
    station_on_source=150,
    side=TurnoutSide.RIGHT,
)