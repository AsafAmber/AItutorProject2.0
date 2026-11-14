"""CPU-only Streamlit Community Cloud entry point.

Run from the repository root: streamlit run cloud/streamlit_app.py
"""
from pathlib import Path
import os
import runpy
import sys

import streamlit as st

APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))

# Read secrets before importing modules that capture configuration at import time.
# Top-level scalar settings use the same names as the local .env configuration.
try:
    for name, value in st.secrets.items():
        if isinstance(value, (str, int, float, bool)):
            os.environ[name] = str(value)
except FileNotFoundError:
    pass  # Local preview can use environment variables or sidebar API-key inputs.

os.environ["CLOUD_DEMO"] = "1"
os.environ["EMBED_DEVICE"] = "cpu"
os.environ.setdefault("LLM_PROVIDER", "openai")
os.environ.setdefault("TRANSLATION_PROVIDER", "tutor")
os.environ.setdefault("RETRIEVAL_MODE", "dense")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("OMP_NUM_THREADS", "2")

runpy.run_path(str(APP_ROOT / "app.py"), run_name="__main__")
