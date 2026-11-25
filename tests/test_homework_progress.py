"""Private save round-trips and real Streamlit question navigation."""
from pathlib import Path
from types import SimpleNamespace

import pytest

import homework_progress as saves


def test_private_save_roundtrip_and_delete(tmp_path):
    first, second = saves.new_code(), saves.new_code()
    data = {"assignment": "hw_1", "question": 2,
            "conversations": {"q2": {"display": [{"role": "user", "content": "שלום"}]}},
            "completed": {"hw_1:pdf": [1]}}
    saves.write_progress(first, data, tmp_path)
    assert saves.read_progress(first, tmp_path) == data
    assert saves.save_path(first, tmp_path).stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileNotFoundError):
        saves.read_progress(second, tmp_path)
    data["question"] = 3
    saves.write_progress(first, data, tmp_path)
    assert saves.read_progress(first, tmp_path)["question"] == 3
    saves.delete_progress(first, tmp_path)
    assert not saves.save_path(first, tmp_path).exists()
    assert not list(tmp_path.glob("*.tmp"))


def test_invalid_or_corrupt_save(tmp_path):
    with pytest.raises(ValueError):
        saves.read_progress("../../private", tmp_path)
    code = saves.new_code()
    for invalid in ['{"version": 2}', '[]', '{"version": 1, "progress": {"conversations": {"q": {"history": [42]}}}}']:
        saves.save_path(code, tmp_path).write_text(invalid)
        with pytest.raises(ValueError):
            saves.read_progress(code, tmp_path)


def test_configured_directory_and_portable_file(tmp_path, monkeypatch):
    monkeypatch.setenv("HOMEWORK_PROGRESS_DIR", str(tmp_path))
    monkeypatch.delenv("HOMEWORK_PROGRESS_DATABASE_URL", raising=False)
    code = saves.new_code()
    data = {"assignment": "HW1", "question": 2, "completed": {}, "conversations": {}}
    saves.write_progress(code, data)
    assert saves.save_path(code).parent == tmp_path
    backup = saves.encode_progress(saves.read_progress(code))
    saves.delete_progress(code)
    assert not saves.save_path(code).exists()
    assert saves.decode_progress(backup.encode("utf-8")) == data


def test_changed_material_invalidates_chat():
    original = saves.context_id("hw_1", 1, "pdf", ["BFS"])
    for args in [("hw_1", 2, "pdf", ["BFS"]), ("hw_2", 1, "pdf", ["BFS"]),
                 ("hw_1", 1, "new-pdf", ["BFS"]), ("hw_1", 1, "pdf", ["DFS"])]:
        assert saves.context_id(*args) != original


@pytest.fixture
def homework_app(monkeypatch, tmp_path):
    from streamlit.testing.v1 import AppTest
    import rag_engine as rag
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("UI_LANGUAGE", "en")
    monkeypatch.setattr(rag, "HybridRetriever", lambda: SimpleNamespace(chunks={}))
    # Save all UI-test progress outside the real user's progress directory.
    monkeypatch.setattr(saves, "write_progress", lambda code, data: _write(code, data, tmp_path))
    monkeypatch.setattr(saves, "read_progress", lambda code: _read(code, tmp_path))
    monkeypatch.setattr(saves, "delete_progress", lambda code: _delete(code, tmp_path))
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=30)
    app.run()
    assert not app.exception
    app.radio(key="study_mode").set_value("homework").run()
    assert not app.exception
    return app, tmp_path


_write, _read, _delete = saves.write_progress, saves.read_progress, saves.delete_progress


def test_question_navigation_and_no_homework_chips(homework_app):
    from langchain_core.messages import HumanMessage, AIMessage
    app, _ = homework_app
    assert app.radio(key="hw_question").value == 1
    assert "Question 1" in app.subheader[0].value
    assert not any(str(b.key).startswith("chip") for b in app.button)
    app.session_state.display = [{"role": "user", "content": "My reasoning", "rtl": False}]
    app.session_state.history = [HumanMessage("My reasoning"), AIMessage("Try an invariant")]
    app.radio(key="hw_question").set_value(2).run()
    assert not app.exception
    assert app.session_state.display == []
    assert "Question 2" in app.subheader[0].value
    assert app.session_state.active_homework_problems == [2]
    app.radio(key="hw_question").set_value(1).run()
    assert app.session_state.display[0]["content"] == "My reasoning"
    assert app.session_state.history[1].content == "Try an invariant"
    assert not app.exception


def test_save_resume_and_opt_out(homework_app):
    from streamlit.testing.v1 import AppTest
    app, directory = homework_app
    app.radio(key="hw_question").set_value(2).run()
    app.checkbox[0].check().run()
    app.session_state.display = [{"role": "user", "content": "Saved question", "rtl": False}]
    app.toggle(key="save_hw_widget").set_value(True).run()
    assert not app.exception
    code = app.session_state.hw_resume_code
    assert _read(code, directory)["question"] == 2
    fresh = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=30).run()
    fresh.radio(key="study_mode").set_value("homework").run()
    next(t for t in fresh.text_input if t.label == "Resume code").set_value(code)
    next(b for b in fresh.button if b.label == "Resume").click().run()
    assert not fresh.exception
    assert fresh.radio(key="hw_question").value == 2
    assert fresh.checkbox[0].value
    assert fresh.session_state.display[0]["content"] == "Saved question"
    fresh.radio(key="study_mode").set_value("learn").run()
    fresh.radio(key="study_mode").set_value("homework").run()
    assert fresh.toggle(key="save_hw_widget").value
    fresh.toggle(key="save_hw_widget").set_value(False).run()
    assert not fresh.exception
    assert not saves.save_path(code, directory).exists()


def test_restore_portable_backup_without_server_storage(homework_app, monkeypatch):
    import streamlit as st

    app, directory = homework_app
    app.radio(key="hw_question").set_value(2).run()
    app.checkbox[0].check().run()
    app.session_state.display = [{"role": "user", "content": "Portable question", "rtl": False}]
    app.run()
    payload = saves.encode_progress(app.session_state.hw_progress).encode("utf-8")
    upload = SimpleNamespace(size=len(payload), getvalue=lambda: payload)
    monkeypatch.setattr(st, "file_uploader", lambda *args, **kwargs: upload)
    app.radio(key="hw_question").set_value(3).run()
    next(b for b in app.button if b.label == "Restore backup").click().run()
    assert not app.exception
    assert app.radio(key="hw_question").value == 2
    assert app.checkbox[0].value
    assert app.session_state.display[0]["content"] == "Portable question"
    assert not app.toggle(key="save_hw_widget").value
    assert not list(directory.glob("*.json"))


def test_generic_help_uses_sidebar_problem(homework_app, monkeypatch):
    import rag_engine as rag
    from homework_material import problem_numbers
    app, _ = homework_app
    observed = []
    monkeypatch.setattr(rag, "get_llm", lambda **kwargs: object())

    def prepare(question, week, retriever, homework, **kwargs):
        observed.append((question, homework))
        return rag.RetrievalDecision("insufficient", normalized_question=question)

    monkeypatch.setattr(rag, "prepare_retrieval", prepare)
    app.radio(key="hw_question").set_value(3).run()
    app.chat_input[0].set_value("Can you give me a hint?").run()
    assert not app.exception
    assert len(observed) == 1
    assert problem_numbers(observed[0][0]) == {3}
    assert [p["number"] for p in observed[0][1]["problem_statements"]] == [3]
    assert len(app.session_state.display) == 2
    app.radio(key="hw_question").set_value(2).run()
    assert app.session_state.display == []


def test_model_reply_math_is_normalized_in_live_and_saved_chat(homework_app, monkeypatch):
    import rag_engine as rag
    app, _ = homework_app
    monkeypatch.setattr(rag, "get_llm", lambda **kwargs: object())
    monkeypatch.setattr(rag, "prepare_retrieval", lambda question, *args, **kwargs:
                        rag.RetrievalDecision("answer", normalized_question=question, assignment_count=1))
    reply = r'Consider \(T(n)=n^2\). Then \[\sum_{i=1}^{n}i=\frac{n(n+1)}{2}\] (Assignment 1)'
    monkeypatch.setattr(rag, "generate_scoped_answer", lambda *args, **kwargs: reply)
    app.chat_input[0].set_value("Give me a hint").run()
    assert not app.exception
    expected = 'Consider $T(n)=n^2$.'
    assert any(expected in m.value and '$$' in m.value for m in app.markdown)
    app.radio(key="hw_question").set_value(2).run()
    app.radio(key="hw_question").set_value(1).run()
    assert any(expected in m.value and '$$' in m.value for m in app.markdown)
    assert not app.exception
    assert app.get("image")  # Original PDF question image remains visible above chat.


def test_hebrew_saved_response_uses_latex(homework_app):
    app, _ = homework_app
    app.session_state.display = [{"role": "assistant", "content": r'זמן הריצה הוא \(O(n \log n)\)', "rtl": True}]
    app.run()
    assert not app.exception
    assert any(r'$O(n \log n)$' in m.value for m in app.markdown)


def test_original_page_button_and_no_extracted_text(homework_app):
    app, _ = homework_app
    app.radio(key="hw_question").set_value(5).run()
    assert not app.exception
    assert app.button(key="toggle_original_pages").label == "Show original pages"
    assert not any("Extracted text" in e.label for e in app.expander)
    compact = str(app.get("image")[0].proto)
    app.button(key="toggle_original_pages").click().run()
    assert not app.exception
    assert app.button(key="toggle_original_pages").label == "Show question only"
    assert str(app.get("image")[0].proto) != compact
    app.button(key="toggle_original_pages").click().run()
    assert not app.exception
    assert str(app.get("image")[0].proto) == compact


def test_answer_body_citations_expand_without_changing_history(homework_app, monkeypatch):
    import rag_engine as rag
    app, _ = homework_app
    chunk = rag.Chunk('test::0', 'Evidence', 1, 'tutorial_1',
                     'Tutorial 1 — Introduction to Algorithm Design and Analysis › Growth Rates — PDF pages 4–5')
    hit = rag.Hit(chunk, 0.9, 0.9)
    monkeypatch.setattr(rag, 'get_llm', lambda **kwargs: object())
    monkeypatch.setattr(rag, 'prepare_retrieval', lambda question, *args, **kwargs:
                        rag.RetrievalDecision('answer', [hit], normalized_question=question, assignment_count=1))
    monkeypatch.setattr(rag, 'generate_scoped_answer', lambda *args, **kwargs:
                        'Use the definition (Source 1). Consider the statement (Assignment 1).')
    app.chat_input[0].set_value('Give me a hint').run()
    assert not app.exception
    responses = [m.value for m in app.markdown if 'Use the definition' in m.value]
    assert responses and 'Tutorial 1 — pages 4–5' in responses[-1]
    assert 'Introduction to Algorithm Design and Analysis' not in responses[-1]
    assert 'pages 4–5' in responses[-1]
    assert 'Homework 1 — pages 1' in responses[-1]
    assert '(Source 1)' not in responses[-1]
    assert '(Source 1)' in app.session_state.history[-1].content
    app.radio(key='hw_question').set_value(2).run()
    app.radio(key='hw_question').set_value(1).run()
    assert not app.exception
    assert any('Use the definition' in m.value and 'Tutorial 1 — pages 4–5' in m.value for m in app.markdown)
