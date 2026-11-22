# MyAlignment

평면선형, 종단, 철도 캔트와 분기기, 코리더, TIN 지표면을 구성하는 Python 라이브러리입니다. 계산 결과를 DXF나 브라우저용 3D HTML로 내보낼 수 있습니다.

## 설치

Python 3.11 이상과 Git이 필요합니다. pip는 `cadgeom`의 고정 리비전을 GitHub에서 가져옵니다.

```bash
python -m pip install .
```

## 사용 설명서

- [시작하기](docs/getting-started.md)에서 선형과 종단을 만들고 코리더를 DXF로 출력합니다.
- [모듈 찾아보기](docs/modules.md)에서 패키지별 진입점과 예제를 확인합니다.
- [문서 홈](docs/index.md)에서 작업별 가이드로 이동합니다.

브라우저에서 문서를 보려면 저장소 루트에서 실행합니다.

```bash
python -m pip install "mkdocs>=1.6,<2"
python -m mkdocs serve
```

기본 주소는 `http://127.0.0.1:8000`입니다. 정적 HTML 파일은 `python -m mkdocs build --strict`로 생성하며 출력 폴더는 `site/`입니다.
