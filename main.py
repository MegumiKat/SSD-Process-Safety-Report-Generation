# main.py
import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon, QFont

from src.ui.ui_main import MainWindow


def main():
    app = QApplication(sys.argv)

    # 基础字体（你也可以不设 30，让窗口内部的 _apply_font_scaling 接管）
    base_font = QFont()
    base_font.setPointSize(16)
    app.setFont(base_font)

    base_dir = Path(__file__).resolve().parent

    # Icon
    icon_path_ico = base_dir / "src" / "assets" / "app.ico"
    icon_path_png = base_dir / "src" / "assets" / "app.png"
    icon_path = icon_path_ico if icon_path_ico.exists() else icon_path_png
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    else:
        print(f"[Warning] Icon file not found: {icon_path_ico} / {icon_path_png}")

    # Dark QSS (Night)
    qss_path = base_dir / "src" /"assets" / "app.qss"
    if qss_path.exists():
        app.setStyleSheet(qss_path.read_text(encoding="utf-8"))
    else:
        print(f"[Warning] QSS file not found: {qss_path}")

    win = MainWindow()
    win.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()