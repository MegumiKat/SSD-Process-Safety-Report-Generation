from pathlib import Path

THIS_FILE = Path(__file__).resolve()

# parents[0] = config 目录
# parents[1] = src 目录
# parents[2] = 项目根目录
SRC_DIR = THIS_FILE.parents[1]
BASE_DIR = THIS_FILE.parents[2]

DATA_DIR = BASE_DIR / "data"
ASSETS_DIR = SRC_DIR / "assets"

DEFAULT_TEMPLATE_PATH = DATA_DIR / "DSC Report-Empty-2512.docx"

# 新增：logo 路径（把文件名改成你实际的 logo 名字）
LOGO_PATH = ASSETS_DIR / "logo.png"