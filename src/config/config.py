# src/config/config.py
from pathlib import Path

THIS_FILE = Path(__file__).resolve()

# 项目根目录：parents[0]=config，1=src，2=项目根目录
BASE_DIR = THIS_FILE.parents[2]

DATA_DIR = BASE_DIR / "data"

DEFAULT_TEMPLATE_PATH = DATA_DIR / "DSC Report-Empty-2512.docx"