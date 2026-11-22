# myalignment Python Package

myalignment는 직선, 원곡선, 완화곡선으로 구성된 선형을 다루는 파이썬 패키지입니다.
다양한 프로젝트에서 공용 라이브러리로 활용할 수 있습니다.

## Features
- `myalignment.alignment.alignment_builder.AlignmentBuilder`로 선형을 생성합니다.
- `myalignment.enitity`의 `LineEntity`, `ArcEntity`, `SpiralEntity`가 선형을 구성합니다.

## Dependence
`cadgeom`의 `Point2d`를 사용합니다.

## Installation
Python 3.11 이상에서 설치할 수 있습니다. pip는 `cadgeom`의 고정 리비전을
GitHub에서 가져오므로 Git과 해당 저장소에 대한 접근이 필요합니다.

```bash
pip install -e .
```
