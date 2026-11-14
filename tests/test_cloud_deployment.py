"""Cloud startup smoke tests without model downloads or paid API requests."""
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

import rag_engine as rag

ENTRY = Path(__file__).resolve().parents[1] / "cloud" / "streamlit_app.py"


@pytest.mark.parametrize("provider,model_key,model", [
    ("openai", "OPENAI_MODEL", "configured-openai-model"),
    ("openrouter", "OPENROUTER_MODEL", "configured/router-model"),
])
def test_cloud_bootstraps_missing_index_and_locks_models(monkeypatch, tmp_path, provider, model_key, model):
    st.cache_resource.clear()
    index = tmp_path / "index"
    chunks = tmp_path / "chunks.jsonl"
    monkeypatch.setattr(rag, "INDEX_DIR", index)
    monkeypatch.setattr(rag, "CHUNKS_FILE", chunks)
    monkeypatch.setattr(rag, "index_needs_rebuild", lambda: not chunks.exists())
    builds = []

    def build(**kwargs):
        builds.append(True)
        index.mkdir()
        chunks.write_text("")

    monkeypatch.setattr(rag, "build_index", build)
    monkeypatch.setattr(rag, "HybridRetriever", lambda: SimpleNamespace(chunks={}))
    with patch.dict(os.environ, {"LLM_PROVIDER": "ollama", "TRANSLATION_PROVIDER": "ollama"}):
        app = AppTest.from_file(str(ENTRY))
        app.secrets.update({"LLM_PROVIDER": provider, model_key: model,
                            "TRANSLATION_PROVIDER": "tutor"})
        app.run(timeout=15)
        assert not app.exception
        assert not app.error
        assert builds == [True]
        assert os.environ["EMBED_DEVICE"] == "cpu"
        widgets = [w for w in app.selectbox if w.value == provider]
        assert len(widgets) == 1
        assert len(widgets[0].options) == 1
        assert all("Ollama" not in option for w in app.selectbox for option in w.options)
        if provider == "openai":
            assert any(w.value == model and w.disabled for w in app.selectbox)
        else:
            assert any(model in caption.value for caption in app.caption)
        app.run(timeout=15)
        assert not app.exception
        assert builds == [True]
    st.cache_resource.clear()


def test_cloud_rejects_local_provider_before_model_loading():
    st.cache_resource.clear()
    with patch.dict(os.environ):
        app = AppTest.from_file(str(ENTRY))
        app.secrets.update({"LLM_PROVIDER": "ollama", "TRANSLATION_PROVIDER": "tutor"})
        app.run(timeout=15)
        assert not app.exception
        assert any("set LLM_PROVIDER" in error.value for error in app.error)
    st.cache_resource.clear()
