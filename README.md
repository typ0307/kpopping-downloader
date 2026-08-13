# 💙 Kpopping Downloader & Viewer

kpopping.com의 고화질 K-POP 아이돌 사진(KPics)을 편하게 감상하고 **원본 화질과 파일명 그대로** 다운로드할 수 있는 데스크톱 애플리케이션입니다.
강력한 봇 우회 로직이 적용되어 서버 차단 없이 안전하게 사진을 수집할 수 있습니다.

## ✨ 주요 기능 (Features)

- **강력한 봇 차단 우회 🛡️**: `cloudscraper`와 무작위 딜레이(Random Delay) 로직을 통해 실제 크롬 브라우저 사용자처럼 작동하여 차단을 방지합니다.
- **원본 파일명 유지**: 다운로드 시 001.jpg 같은 임의의 이름이 아닌, 서버에 등록된 원본 이미지 파일명을 그대로 유지하여 저장합니다.
- **선택적 다운로드 및 제어**:
  - `현재 사진 1장 다운로드`: 뷰어에 띄워진 사진 한 장만 즉시 저장합니다.
  - `전체 다운로드`: 게시글 제목으로 폴더를 자동 생성하고 앨범 내 전체 고화질 사진을 저장합니다.
  - `다운로드 중지`: 대용량 앨범 다운로드 중 언제든 작업을 즉시 중단할 수 있습니다.
- **고화질 뷰어 & 썸네일 슬라이더**: 마우스 드래그로 뷰어와 썸네일 영역 크기를 자유롭게 조절하며 사진을 감상할 수 있습니다.

## 🛠️ 요구 사항 (Prerequisites)

- Python 3.8 이상
- [uv](https://github.com/astral-sh/uv) (가르고 가벼운 파이썬 패키지 매니저)

## 🚀 설치 및 실행 방법 (Installation & Usage)

**1. 프로젝트 클론 및 폴더 이동**
\`\`\`bash
git clone https://github.com/본인계정명/kpopping-downloader.git
cd kpopping-downloader
\`\`\`

**2. 패키지 설치 및 실행 (Windows / Mac 공통)**
\`\`\`bash

# 의존성 패키지 설치 (PySide6, bs4, cloudscraper 등)

uv add PySide6 beautifulsoup4 cloudscraper

# 프로그램 실행

uv run main.py
\`\`\`

**3. 사용 방법**

1. kpopping.com의 앨범 주소를 복사하여 상단 입력창에 붙여넣고 **[불러오기]** 클릭.
2. 썸네일을 클릭하며 메인 뷰어에서 고화질로 감상.
3. 원하는 폴더 경로를 지정한 뒤 **[다운로드]** 버튼을 눌러 사진 저장.

## 📦 단일 실행 파일(.exe) 빌드 방법 (Windows)

파이썬 설치 없이 윈도우에서 바로 실행 가능한 `.exe` 파일을 만들려면 아래 명령어를 사용하세요.

\`\`\`bash

# 빌드용 패키지 추가

uv add --dev pyinstaller

# 실행 파일 빌드 (검은색 콘솔창 숨김)

uv run pyinstaller --noconsole --onefile --windowed main.py
\`\`\`

> 빌드가 완료되면 `dist/` 폴더 내에 `main.exe` 파일이 생성됩니다.
