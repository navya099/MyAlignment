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
python -m pip install -r requirements-docs.txt
python -m mkdocs serve
```

기본 주소는 `http://127.0.0.1:8000`입니다. 정적 HTML 파일은 `python -m mkdocs build --strict`로 생성하며 출력 폴더는 `site/`입니다.

HTML의 **API 레퍼런스** 메뉴에서 패키지별 클래스와 공개 메서드, 속성을 검색할 수 있습니다. API 페이지는 빌드할 때 소스에서 생성합니다.

## 배포 검증

새 가상환경에 `python -m pip install .`로 설치한 뒤 `python scripts/check_installed_examples.py`를 실행하면 가이드 예제와 시작하기 예제의 DXF 출력을 확인합니다. GitHub Actions에서도 패키지 설치, 예제, 회귀 테스트, 문서 빌드를 검증합니다.

문서 사이트를 공개하려면 저장소의 **Settings → Pages**에서 소스를 **GitHub Actions**로 지정하고 기본 브랜치에 있는 **Publish documentation to GitHub Pages** 워크플로를 실행합니다. 게시 주소는 워크플로의 배포 결과에 표시됩니다.
