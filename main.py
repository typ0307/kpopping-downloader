import os
import random
import re
import sys
import time
from urllib.parse import unquote

import cloudscraper
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

# 봇 탐지 우회를 위한 크롬 브라우저 위장 스크래퍼
scraper = cloudscraper.create_scraper(
    browser={"browser": "chrome", "platform": "windows", "desktop": True}
)

HEADERS = {
    "Referer": "https://kpopping.com/",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
}


class FetchThread(QThread):
    """HTML 파싱 및 고화질 이미지 URL 리스트 추출"""

    finished_signal = Signal(str, list)
    error_signal = Signal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            res = scraper.get(self.url, headers=HEADERS, timeout=10)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, "html.parser")

            title_tag = soup.find("h1")
            title = title_tag.text.strip() if title_tag else "Karina_Downloaded"
            title = re.sub(r'[\\/*?:"<>|]', "", title)

            img_urls = []

            main_article = soup.find("article")
            target_soup = main_article if main_article else soup

            for section in target_soup.find_all("section"):
                section.decompose()

            for img in target_soup.find_all("img"):
                src = img.get("src", "")

                if "url=" in src and "cdn.kpopping.com" in src:
                    match = re.search(r"url=([^&]+)", src)
                    if match:
                        decoded_url = unquote(match.group(1))
                        if decoded_url not in img_urls:
                            img_urls.append(decoded_url)
                elif "cdn.kpopping.com/kpics" in src and "url=" not in src:
                    if src not in img_urls:
                        img_urls.append(src)

            if not img_urls:
                raise ValueError("이미지를 찾을 수 없습니다. 주소를 확인해주세요.")

            self.finished_signal.emit(title, img_urls)
        except Exception as e:
            self.error_signal.emit(f"페이지 접근 실패:\n{e!s}")


class ThumbnailLoaderThread(QThread):
    """리스트 위젯용 썸네일 비동기 다운로드"""

    thumb_loaded = Signal(int, QPixmap, str)

    def __init__(self, urls):
        super().__init__()
        self.urls = urls
        self.is_cancelled = False

    def run(self):
        for idx, url in enumerate(self.urls):
            if self.is_cancelled:
                break
            try:
                time.sleep(random.uniform(0.1, 0.3))
                encoded_url = url.replace(":", "%3A").replace("/", "%2F")
                thumb_url = (
                    f"https://kpopping.com/_next/image?url={encoded_url}&w=256&q=75"
                )

                res = scraper.get(thumb_url, headers=HEADERS, timeout=5)
                if res.status_code == 200:
                    img = QImage()
                    img.loadFromData(res.content)
                    self.thumb_loaded.emit(idx, QPixmap.fromImage(img), url)
            except Exception:
                continue

    def cancel(self):
        self.is_cancelled = True


class DownloadThread(QThread):
    """원본 고화질 이미지 전체 저장 (Rate Limit 우회 및 중단 기능 포함)"""

    progress_signal = Signal(int)
    finished_signal = Signal(bool)
    error_signal = Signal(str)

    def __init__(self, urls, save_dir):
        super().__init__()
        self.urls = urls
        self.save_dir = save_dir
        self.is_cancelled = False

    def run(self):
        try:
            os.makedirs(self.save_dir, exist_ok=True)
            total = len(self.urls)

            for idx, url in enumerate(self.urls, 1):
                if self.is_cancelled:
                    self.finished_signal.emit(False)
                    return

                time.sleep(random.uniform(0.5, 1.5))

                res = scraper.get(url, headers=HEADERS, timeout=15)
                res.raise_for_status()

                original_filename = url.split("/")[-1].split("?")[0]
                file_path = os.path.join(self.save_dir, original_filename)

                with open(file_path, "wb") as f:
                    f.write(res.content)

                self.progress_signal.emit(int((idx / total) * 100))

            self.finished_signal.emit(True)
        except Exception as e:
            self.error_signal.emit(f"다운로드 중 오류:\n{e!s}")

    def cancel(self):
        self.is_cancelled = True


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kpopping Downloader 💙")
        self.resize(1200, 900)
        self.urls = []
        self.current_title = ""
        self.current_image_url = ""

        self.fetch_thread = None
        self.thumb_thread = None
        self.download_thread = None

        self.setup_ui()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 상단 (입력부)
        url_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("kpopping.com 주소를 입력하세요...")
        self.btn_load = QPushButton("불러오기")
        self.btn_load.clicked.connect(self.load_url)
        url_layout.addWidget(self.url_input)
        url_layout.addWidget(self.btn_load)
        main_layout.addLayout(url_layout)

        # 중앙 및 하단 (스플리터 제어)
        splitter = QSplitter(Qt.Vertical)

        self.image_viewer = QLabel("주소를 입력하고 불러오기를 클릭하세요")
        self.image_viewer.setAlignment(Qt.AlignCenter)
        self.image_viewer.setStyleSheet(
            "background-color: #f3f4f6; border-radius: 12px; font-weight: bold; color: #6b7280;"
        )
        splitter.addWidget(self.image_viewer)

        self.thumbnail_list = QListWidget()
        self.thumbnail_list.setViewMode(QListWidget.IconMode)
        self.thumbnail_list.setIconSize(QSize(120, 120))
        self.thumbnail_list.setFlow(QListWidget.LeftToRight)
        self.thumbnail_list.setSpacing(10)
        self.thumbnail_list.itemClicked.connect(self.on_thumbnail_clicked)
        splitter.addWidget(self.thumbnail_list)

        splitter.setSizes([700, 150])
        main_layout.addWidget(splitter, stretch=1)

        # 최하단 (경로 및 다운로드 제어부)
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

        self.btn_stop = QPushButton("다운로드 중지")
        self.btn_stop.clicked.connect(self.stop_download)
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet("color: red; font-weight: bold;")

        save_layout.addWidget(self.path_input)
        save_layout.addWidget(self.btn_browse)
        save_layout.addWidget(self.btn_download_single)
        save_layout.addWidget(self.btn_download_all)
        save_layout.addWidget(self.btn_stop)
        main_layout.addLayout(save_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)

    def load_url(self):
        url = self.url_input.text().strip()
        if not url:
            return

        # 기존 스레드가 돌고 있다면 중단
        if self.thumb_thread and self.thumb_thread.isRunning():
            self.thumb_thread.cancel()

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

        if self.urls:
            self.load_main_image(self.urls[0])

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
            res = scraper.get(url, headers=HEADERS, timeout=5)
            img = QImage()
            img.loadFromData(res.content)
            self.current_pixmap = QPixmap.fromImage(img)

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
            original_filename = self.current_image_url.split("/")[-1].split("?")[0]
            file_path = os.path.join(save_dir, original_filename)

            res = scraper.get(self.current_image_url, headers=HEADERS, timeout=10)
            res.raise_for_status()

            with open(file_path, "wb") as f:
                f.write(res.content)

            QMessageBox.information(self, "성공", f"저장 완료:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "오류", f"저장 실패:\n{e!s}")

    def download_images(self):
        base_dir = self.path_input.text().strip()
        save_dir = os.path.join(base_dir, self.current_title)

        self.btn_download_all.setEnabled(False)
        self.btn_download_single.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.progress_bar.setValue(0)

        self.download_thread = DownloadThread(self.urls, save_dir)
        self.download_thread.progress_signal.connect(self.progress_bar.setValue)
        self.download_thread.finished_signal.connect(self.on_download_finished)
        self.download_thread.error_signal.connect(self.on_download_error)
        self.download_thread.start()

    def stop_download(self):
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.cancel()
            self.btn_stop.setEnabled(False)

    def on_download_finished(self, completed):
        self.btn_download_all.setEnabled(True)
        self.btn_download_single.setEnabled(True)
        self.btn_stop.setEnabled(False)

        if completed:
            QMessageBox.information(
                self, "완료", f"[{self.current_title}] 전체 다운로드 완료!"
            )
        else:
            QMessageBox.warning(
                self, "중단", "다운로드가 사용자에 의해 중단되었습니다."
            )

    def on_error(self, err_msg):
        self.btn_load.setEnabled(True)
        self.btn_download_all.setEnabled(bool(self.urls))
        self.btn_download_single.setEnabled(bool(self.urls))
        QMessageBox.critical(self, "오류", err_msg)

    def on_download_error(self, err_msg):
        self.btn_download_all.setEnabled(True)
        self.btn_download_single.setEnabled(True)
        self.btn_stop.setEnabled(False)
        QMessageBox.critical(self, "오류", err_msg)

    def resizeEvent(self, event):
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
