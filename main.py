import os
import re
import sys
from urllib.parse import unquote

import requests
from bs4 import BeautifulSoup
from PySide6.QtCore import QSize, Qt, QThread, Signal
from PySide6.QtGui import QIcon, QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

# 봇 차단(Anti-Bot) 우회를 위한 헤더 설정
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
}


class FetchThread(QThread):
    """HTML을 파싱하여 제목과 고화질 이미지 URL 리스트를 가져오는 스레드"""

    finished_signal = Signal(str, list)
    error_signal = Signal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            res = requests.get(self.url, headers=HEADERS, timeout=10)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, "html.parser")

            # 제목 추출 및 폴더명 안전 처리 (특수문자 제거)
            title_tag = soup.find("h1")
            title = title_tag.text.strip() if title_tag else "Karina_Downloaded"
            title = re.sub(r'[\\/*?:"<>|]', "", title)

            img_urls = []

            # 메인 갤러리가 있는 <article> 태그만 추출
            main_article = soup.find("article")
            target_soup = main_article if main_article else soup

            # 불필요한 추천 앨범 등의 <section> 태그 제거
            for section in target_soup.find_all("section"):
                section.decompose()

            # 정제된 영역 안에서 이미지 추출
            for img in target_soup.find_all("img"):
                src = img.get("src", "")

                # 원본 URL이 url 파라미터에 인코딩되어 숨겨져 있는 경우
                if "url=" in src and "cdn.kpopping.com" in src:
                    match = re.search(r"url=([^&]+)", src)
                    if match:
                        decoded_url = unquote(match.group(1))
                        if decoded_url not in img_urls:
                            img_urls.append(decoded_url)
                # 원본 URL이 직접 노출된 경우
                elif "cdn.kpopping.com/kpics" in src and "url=" not in src:
                    if src not in img_urls:
                        img_urls.append(src)

            if not img_urls:
                raise ValueError("이미지를 찾을 수 없습니다. 주소를 다시 확인해주세요.")

            self.finished_signal.emit(title, img_urls)
        except Exception as e:
            self.error_signal.emit(str(e))


class ThumbnailLoaderThread(QThread):
    """리스트 위젯에 섬네일을 비동기로 로드하는 스레드"""

    thumb_loaded = Signal(int, QPixmap, str)

    def __init__(self, urls):
        super().__init__()
        self.urls = urls

    def run(self):
        for idx, url in enumerate(self.urls):
            try:
                # 빠른 로딩을 위해 Next.js 최적화 썸네일 API 활용 (가로 256px 기준)
                encoded_url = url.replace(":", "%3A").replace("/", "%2F")
                thumb_url = (
                    f"https://kpopping.com/_next/image?url={encoded_url}&w=256&q=75"
                )

                res = requests.get(thumb_url, headers=HEADERS, timeout=5)
                if res.status_code == 200:
                    img = QImage()
                    img.loadFromData(res.content)
                    pixmap = QPixmap.fromImage(img)
                    self.thumb_loaded.emit(idx, pixmap, url)
            except Exception:
                pass  # 섬네일 로드 실패 시 무시


class DownloadThread(QThread):
    """원본 고화질 이미지를 폴더에 전체 저장하는 스레드"""

    progress_signal = Signal(int)
    finished_signal = Signal()
    error_signal = Signal(str)

    def __init__(self, urls, save_dir):
        super().__init__()
        self.urls = urls
        self.save_dir = save_dir

    def run(self):
        try:
            os.makedirs(self.save_dir, exist_ok=True)
            total = len(self.urls)
            for idx, url in enumerate(self.urls, 1):
                res = requests.get(url, headers=HEADERS, timeout=15)
                res.raise_for_status()

                ext = url.split(".")[-1]
                if len(ext) > 4:
                    ext = "jpg"

                file_path = os.path.join(self.save_dir, f"{idx:03d}.{ext}")
                with open(file_path, "wb") as f:
                    f.write(res.content)

                self.progress_signal.emit(int((idx / total) * 100))
            self.finished_signal.emit()
        except Exception as e:
            self.error_signal.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kpopping Downloader 💙")
        self.resize(1200, 900)
        self.urls = []
        self.current_title = ""
        self.current_image_url = ""  # 현재 보고 있는 사진의 URL
        self.setup_ui()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 상단: URL 입력
        url_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("kpopping.com 주소를 입력하세요...")
        self.btn_load = QPushButton("불러오기")
        self.btn_load.clicked.connect(self.load_url)
        url_layout.addWidget(self.url_input)
        url_layout.addWidget(self.btn_load)
        main_layout.addLayout(url_layout)

        # 뷰어와 썸네일 크기 조절을 위한 수직 Splitter
        splitter = QSplitter(Qt.Vertical)

        # 중앙: 메인 이미지 뷰어
        self.image_viewer = QLabel("주소를 입력하고 불러오기를 클릭하세요")
        self.image_viewer.setAlignment(Qt.AlignCenter)
        self.image_viewer.setStyleSheet(
            "background-color: #f3f4f6; border-radius: 12px; font-weight: bold; color: #6b7280;"
        )
        splitter.addWidget(self.image_viewer)

        # 하단: 썸네일 슬라이더
        self.thumbnail_list = QListWidget()
        self.thumbnail_list.setViewMode(QListWidget.IconMode)
        self.thumbnail_list.setIconSize(QSize(120, 120))
        self.thumbnail_list.setFlow(QListWidget.LeftToRight)
        self.thumbnail_list.setSpacing(10)
        self.thumbnail_list.itemClicked.connect(self.on_thumbnail_clicked)
        splitter.addWidget(self.thumbnail_list)

        # Splitter 비율 설정 (뷰어 크게, 썸네일 작게)
        splitter.setSizes([700, 150])
        main_layout.addWidget(splitter, stretch=1)

        # 최하단: 저장 경로 및 다운로드 제어부
        save_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setText(os.path.expanduser("~/Downloads"))

        self.btn_browse = QPushButton("경로 선택")
        self.btn_browse.clicked.connect(self.browse_folder)

        self.btn_download_single = QPushButton("현재 사진 1장 다운로드")
        self.btn_download_single.clicked.connect(self.download_single_image)
        self.btn_download_single.setEnabled(False)

        self.btn_download_all = QPushButton("전체 다운로드")
        self.btn_download_all.clicked.connect(self.download_images)
        self.btn_download_all.setEnabled(False)

        save_layout.addWidget(self.path_input)
        save_layout.addWidget(self.btn_browse)
        save_layout.addWidget(self.btn_download_single)
        save_layout.addWidget(self.btn_download_all)
        main_layout.addLayout(save_layout)

        # 프로그레스 바
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)

    def load_url(self):
        url = self.url_input.text().strip()
        if not url:
            return

        self.btn_load.setEnabled(False)
        self.image_viewer.setText("로딩 중...")
        self.thumbnail_list.clear()
        self.urls = []
        self.current_image_url = ""

        self.fetch_thread = FetchThread(url)
        self.fetch_thread.finished_signal.connect(self.on_fetch_finished)
        self.fetch_thread.error_signal.connect(self.on_error)
        self.fetch_thread.start()

    def on_fetch_finished(self, title, img_urls):
        self.current_title = title
        self.urls = img_urls
        self.btn_load.setEnabled(True)
        self.btn_download_all.setEnabled(True)
        self.btn_download_single.setEnabled(True)

        # 첫 번째 이미지를 뷰어에 로드
        if self.urls:
            self.load_main_image(self.urls[0])

        # 썸네일 비동기 로딩
        self.thumb_thread = ThumbnailLoaderThread(self.urls)
        self.thumb_thread.thumb_loaded.connect(self.add_thumbnail)
        self.thumb_thread.start()

    def add_thumbnail(self, idx, pixmap, url):
        item = QListWidgetItem()
        item.setIcon(QIcon(pixmap))
        item.setData(Qt.UserRole, url)
        self.thumbnail_list.addItem(item)

    def on_thumbnail_clicked(self, item):
        url = item.data(Qt.UserRole)
        self.image_viewer.setText("고화질 이미지 로딩 중...")
        self.load_main_image(url)

    def load_main_image(self, url):
        self.current_image_url = url
        try:
            res = requests.get(url, headers=HEADERS, timeout=5)
            img = QImage()
            img.loadFromData(res.content)
            self.current_pixmap = QPixmap.fromImage(
                img
            )  # 리사이즈 이벤트를 위해 원본 저장

            scaled_pixmap = self.current_pixmap.scaled(
                self.image_viewer.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.image_viewer.setPixmap(scaled_pixmap)
        except Exception:
            self.image_viewer.setText("이미지 로드 실패")

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "저장 경로 선택")
        if folder:
            self.path_input.setText(folder)

    def download_single_image(self):
        if not self.current_image_url:
            return

        base_dir = self.path_input.text().strip()
        save_dir = os.path.join(base_dir, self.current_title)
        os.makedirs(save_dir, exist_ok=True)

        try:
            idx = self.urls.index(self.current_image_url) + 1
            ext = self.current_image_url.split(".")[-1]
            if len(ext) > 4:
                ext = "jpg"

            file_path = os.path.join(save_dir, f"{idx:03d}.{ext}")

            res = requests.get(self.current_image_url, headers=HEADERS, timeout=10)
            res.raise_for_status()

            with open(file_path, "wb") as f:
                f.write(res.content)

            QMessageBox.information(
                self, "성공", f"현재 사진 1장이 저장되었습니다!\n\n경로: {file_path}"
            )
        except Exception as e:
            QMessageBox.critical(self, "오류", f"저장 중 오류가 발생했습니다:\n{e!s}")

    def download_images(self):
        base_dir = self.path_input.text().strip()
        save_dir = os.path.join(base_dir, self.current_title)

        self.btn_download_all.setEnabled(False)
        self.btn_download_single.setEnabled(False)
        self.progress_bar.setValue(0)

        self.download_thread = DownloadThread(self.urls, save_dir)
        self.download_thread.progress_signal.connect(self.progress_bar.setValue)
        self.download_thread.finished_signal.connect(self.on_download_finished)
        self.download_thread.error_signal.connect(self.on_error)
        self.download_thread.start()

    def on_download_finished(self):
        self.btn_download_all.setEnabled(True)
        self.btn_download_single.setEnabled(True)
        QMessageBox.information(
            self, "완료", f"[{self.current_title}] 앨범 전체 다운로드가 완료되었습니다!"
        )

    def on_error(self, err_msg):
        self.btn_load.setEnabled(True)
        self.btn_download_all.setEnabled(bool(self.urls))
        self.btn_download_single.setEnabled(bool(self.urls))
        QMessageBox.critical(self, "오류", f"오류가 발생했습니다:\n{err_msg}")

    def resizeEvent(self, event):
        # 창이나 Splitter 크기가 변경될 때 이미지 비율을 맞춰서 다시 그려줌
        if hasattr(self, "current_pixmap") and not self.current_pixmap.isNull():
            scaled_pixmap = self.current_pixmap.scaled(
                self.image_viewer.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.image_viewer.setPixmap(scaled_pixmap)
        super().resizeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
