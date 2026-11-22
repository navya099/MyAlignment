# 모듈 찾아보기

주요 진입점 열의 경로 앞에 `myalignment.`를 붙입니다. 예를 들어 `alignment.alignment_builder.AlignmentBuilder`는 `from myalignment.alignment_builder import AlignmentBuilder`로 가져옵니다. 하위 패키지의 주요 진입점과 해당 작업의 실행 예제를 연결했습니다.

| 패키지 | 주요 진입점 | 예제와 설명 |
| --- | --- | --- |
| `alignment` | `alignment.alignment_builder.AlignmentBuilder`, `alignment.alignment.Alignment`, `alignment.station_equation.StationEquation`, `alignment.alignment_side.AlignmentSide` | [선형 생성, 변환과 조회](alignment.md) |
| `alignment.style` | `alignment.style.alignment_style.AlignmentStyle`, `alignment.style.display_rule.DisplayRule` | [평면 표시 규칙과 레이블](rendering.md) |
| `enitity` | `enitity.line_entity.LineEntity`, `enitity.arc_entity.ArcEntity`, `enitity.spiral_entity.SpiralEntity`, `enitity.entity_collection.AlignmentEntityCollection` | [선형 요소와 측점 조회](alignment.md) |
| `geometry`, `enum`, `ipdata` | `geometry.arc_geometry.ArcGeometry`, `geometry.spiral_geometry.SpiralGeometry`, `enum.spiraltype.SpiralType`, `ipdata.ipdata.PIInput` | [평면선형 입력 제원](alignment.md) |
| `core`, `exception` | `core.projection_result.ProjectionResult`, `core.station_offset.StationOffsetPoint`, `exception.alignment_error.AlignmentError` | [투영 결과와 선형 입력 검증](alignment.md) |
| `profile` | `profile.profile.ProfileBuilder`, `profile.profiletype.ProfileType`, `profile.view_style.ProfileViewStyle`, `profile.view_band.ProfileViewBand`, `profile.station_label.StationElevationLabel` | [종단 기하, 밴드와 레이블](profile.md) |
| `rail`, `cant` | `rail.rail_alignment.RailAlignment`, `cant.curve.CantCurve`, `cant.curve.CantCriticalStation` | [철도 선형과 캔트](rail.md) |
| `turnout` | `turnout.turnout.Turnout`, `turnout.type.TurnoutType`, `turnout.table.TurnoutTable`, `turnout.crossover_builder.CrossoverBuilder`, `turnout.scissors_builder.ScissorsCrossoverBuilder` | [제원표와 시저스 자동 배치](rail.md) |
| `superelevation` | `superelevation.curve.SuperelevationCurve`, `superelevation.critical_station.SuperelevationCriticalStation`, `superelevation.collection.SuperelevationCollection` | [도로 편구배 데이터](#도로-편구배) |
| `assembly` | `assembly.assembly.AssemblyBuilder`, `assembly.subassembly.Subassembly`, `assembly.codes.PointCode`, `assembly.codes.LinkCode`, `assembly.codes.ShapeCode` | [차로, 사면, 궤도 조립](corridor.md) |
| `corridor` | `corridor.corridor_builder.CorridorBuilder`, `corridor.rail_corridor_builder.RailCorridorBuilder`, `corridor.surface_builder.CorridorSurfaceSpec`, `corridor.corridor_3d_preview.Corridor3DPreview` | [기준선, 영역 및 표면 추출](corridor.md) |
| `target` | `target.mapping.TargetMapping`, `target.reference.TargetReference`, `target.target_type.TargetType` | [타깃 매핑](corridor.md#타깃-매핑) |
| `surface`, `featureline` | `surface.tin_surface.TinSurface`, `surface.tin_surface_builder.TinSurfaceBuilder`, `surface.boundary.Boundary`, `featureline.builder.FeatureLineBuilder` | [TIN 경계, 브레이크라인과 형상선](surface.md) |
| `grading` | `grading.footprint.Footprint`, `grading.grading.Grading`, `grading.criteria_surface.SlopeToSurface`, `grading.site.SiteBuilder` | [사면과 부지 정지](surface.md#사면과-부지-정지) |
| `quantity` | `quantity.takeoff.QuantityTakeoff`, `quantity.material.Material`, `quantity.material.UnitType`, `quantity.report.QTOReport` | [재료 수량과 절·성토량](quantities.md) |
| `structure` | `structure.bridge.Bridge`, `structure.tunnel.Tunnel`, `structure.factory.StructureFactory`, `structure.structurecollection.StructureCollection` | [구조물 생성과 선형 연결](alignment.md#좌표-조회와-편집) |
| `section` | `section.section_view_builder.SectionViewBuilder`, `section.section_view_composer.SectionViewComposer`, `section.section_view_style.SectionViewStyle` | [횡단면 데이터와 출력](rendering.md#횡단-뷰-3d-dxf와-브라우저-미리보기) |
| `render`, `export` | `render.composer.SceneComposer`, `render.profile_view_renderer.ProfileViewRenderer`, `export.dxf_writer.DxfWriter`, `export.dxf_3d_writer.Dxf3DWriter`, `export.json_3d_exporter.Json3DExporter` | [도면과 3D 출력](rendering.md) |
| `utils` | `utils.coordinate_utils.convert_coordinates`, `utils.vector2.Vector2`, `utils.vector3.Vector3`, `utils.curvedirection.CurveDirection` | [EPSG 좌표 변환](#좌표-변환) |

`enitity`는 현재 패키지의 철자입니다. 일반적인 작업은 `AlignmentBuilder`에서 시작하고, 직접 만든 요소를 조립해야 할 때 `AlignmentEntityCollection`을 사용합니다.

## 도로 편구배

```python
from myalignment.alignment_builder import AlignmentBuilder
from myalignment.superelevation.critical_station import (
    CrossSegmentType, SuperelevationCriticalStation, TransitionRegionType,
)
from myalignment.superelevation.curve import SuperelevationCurve

curve = SuperelevationCurve(
    name="Curve", start_station=20, end_station=80,
    critical_stations=(
        SuperelevationCriticalStation(20, TransitionRegionType.TRANSITION_IN),
        SuperelevationCriticalStation(
            50, TransitionRegionType.FULL_SUPERELEVATION,
            {CrossSegmentType.RIGHT_OUT_LANE: -0.04},
        ),
        SuperelevationCriticalStation(80, TransitionRegionType.TRANSITION_OUT),
    ),
)
axis = (
    AlignmentBuilder("Road").with_pi_coords([(0, 0), (100, 0)])
    .with_superelevation_curve(curve).build()
)
critical = axis.superelevation_at(49)
assert critical.station == 50
assert critical.get_slope(CrossSegmentType.RIGHT_OUT_LANE) == -0.04
```

`superelevation_at()`은 해당 구간의 최근접 임계 측점을 조회합니다. 코리더의 `cant_curve`는 철도 캔트용 설정입니다.

## 좌표 변환

```python
from myalignment.utils.coordinate_utils import convert_coordinates

lonlat = (127.0, 37.5)
x, y = convert_coordinates(lonlat, src=4326, target=5186)
restored = convert_coordinates((x, y), src=5186, target=4326)
assert all(abs(a - b) < 1e-8 for a, b in zip(restored, lonlat))
```

위경도 입력은 경도, 위도 순서입니다. 변환한 좌표로 선형을 생성할 경우 측점과 횡거의 프로젝트 단위를 좌표계와 맞춥니다.
