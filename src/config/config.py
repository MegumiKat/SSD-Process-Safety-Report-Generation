from pathlib import Path
import sys

THIS_FILE = Path(__file__).resolve()

def _get_base_dir() -> Path:
    """
    兼容：源码运行 vs PyInstaller 打包运行
    - 源码运行：BASE_DIR = 项目根目录（src 的上一层）
    - 打包运行：BASE_DIR = sys._MEIPASS（PyInstaller 解包后的根）
    """
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    # parents[0]=config, parents[1]=src, parents[2]=项目根目录
    return THIS_FILE.parents[2]

BASE_DIR = _get_base_dir()
SRC_DIR = BASE_DIR / "src"   # 打包时我们会把 src 作为数据一起带进去（见下）
DATA_DIR = BASE_DIR / "data"
ASSETS_DIR = SRC_DIR / "assets"

DEFAULT_TEMPLATE_PATH = DATA_DIR / "DSC Report-Empty-2512.docx"
LOGO_PATH = ASSETS_DIR / "logo.png"
QSS_PATH = ASSETS_DIR / "app.qss"  # 如果你也有 qss