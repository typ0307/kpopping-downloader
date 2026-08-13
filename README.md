# 💙 Kpopping Downloader & Viewer

kpopping.com의 고화질 K-POP 아이돌 사진(KPics)을 편하게 감상하고 원본 화질 그대로 다운로드할 수 있는 데스크톱 애플리케이션입니다.
최신 파이썬 패키지 매니저인 `uv`와 `PySide6`를 기반으로 제작되었습니다.

## ✨ 주요 기능 (Features)

- **고화질 뷰어 지원**: 주소만 입력하면 고화질 원본 사진을 메인 화면에서 바로 감상할 수 있습니다.
- **반응형 썸네일 슬라이더**: 하단 썸네일을 통해 사진을 빠르게 탐색할 수 있으며, 마우스 드래그로 뷰어와 썸네일 영역의 크기를 자유롭게 조절할 수 있습니다.
- **선택적 다운로드**:
  - `현재 사진 1장 다운로드`: 뷰어에 띄워진 맘에 드는 사진 한 장만 즉시 저장합니다.
  - `전체 다운로드`: 게시글 제목으로 폴더를 자동 생성하고, 앨범 내의 모든 고화질 사진을 일괄 저장합니다.
- **스마트 크롤링**: 하단의 불필요한 추천 앨범 사진을 제외하고, 본문의 타겟 사진만 정확하게 추출합니다.

## 🛠️ 요구 사항 (Prerequisites)

- Python 3.8 이상
- [uv](https://github.com/astral-sh/uv) (가르고 가벼운 파이썬 패키지 매니저)

## 🚀 설치 및 실행 방법 (Installation & Usage)

**1. 프로젝트 클론 및 폴더 이동**
\`\`\`bash
git clone https://github.com/본인계정명/kpopping-downloader.git
cd kpopping-downloader
\`\`\`

**2. 패키지 동기화 및 실행 (Windows / Mac 공통)**
\`\`\`bash

# uv를 통해 필요한 패키지(PySide6, requests 등) 자동 설치 및 실행

uv run main.py
\`\`\`

**3. 사용 방법**

1. kpopping.com의 앨범 주소를 복사합니다. (예: `https://kpopping.com/kpics/260811-karina...`)
2. 프로그램 상단 입력창에 붙여넣고 **[불러오기]** 버튼을 클릭합니다.
3. 썸네일을 클릭하며 사진을 감상하거나, 원하는 폴더 경로를 지정한 뒤 **[다운로드]** 버튼을 누릅니다.

## 📦 단일 실행 파일(.exe) 빌드 방법 (Windows)

파이썬이 설치되지 않은 환경에서도 실행 가능한 독립적인 `.exe` 파일을 만들고 싶다면 아래 명령어를 실행하세요.

\`\`\`bash

# 1. 빌드용 패키지(PyInstaller) 설치

uv add --dev pyinstaller

# 2. 실행 파일 빌드 (콘솔창 숨김 처리)

uv run pyinstaller --noconsole --onefile --windowed main.py
\`\`\`

> 빌드가 완료되면 `dist/` 폴더 안에 `main.exe` 파일이 생성됩니다.
