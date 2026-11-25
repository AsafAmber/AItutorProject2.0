"""CPU-only Streamlit Community Cloud entry point.

Run from the repository root: streamlit run cloud/streamlit_app.py
"""
from pathlib import Path
import os
import runpy
import sys

APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))

os.environ["CLOUD_DEMO"] = "1"
os.environ["EMBED_DEVICE"] = "cpu"
os.environ.setdefault("RETRIEVAL_MODE", "dense")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("OMP_NUM_THREADS", "2")

runpy.run_path(str(APP_ROOT / "app.py"), run_name="__main__")
