import pytest

from citation_display import expand_citations
from rag_engine import EvidenceError, validate_citations


SOURCES = [
    {'section': 'Source 1 — Tutorial 7 — Minimum Spanning Trees › Core Concepts — PDF pages 2–4'},
    {'section': 'Source 2 — Tutorial 6 — Graph Traversal › BFS — PDF page 12'},
    {'section': 'Assignment 1 — Homework 1 — HW1.pdf, Problem 3, PDF pages 2'},
]


def test_body_citations_use_short_names_and_locations():
    answer = 'According to Source 1, this holds (Source 2). See [Assignment 1].'
    validate_citations(answer, 2, 1)
    shown = expand_citations(answer, SOURCES)
    assert 'According to Tutorial 7 — pages 2–4' in shown
    assert '(Tutorial 6 — pages 12)' in shown
    assert '(Homework 1 — pages 2)' in shown
    assert 'Source 1' not in shown and 'Assignment 1' not in shown
    assert 'Source 2' in answer  # Original remains available for validation/history.


def test_grouped_and_hebrew_references():
    text = expand_citations('לפי (מקור 1) וגם (Sources 1 and 2), ראו (מטלה 1).', SOURCES, 'he')
    assert 'תרגול 7 — עמודים 2–4' in text
    assert 'תרגול 6 — עמודים 12' in text
    assert 'מטלה 1 — עמודים 2' in text
    assert 'Sources 1' not in text


def test_unknown_ids_cannot_resolve_or_bypass_validation():
    with pytest.raises(EvidenceError):
        validate_citations('Made up (Source 9).', 2)
    assert expand_citations('(Source 9)', SOURCES) == '(Source 9)'
    assert expand_citations('(Assignment 2)', SOURCES) == '(Assignment 2)'


def test_page_is_never_invented_and_code_is_preserved():
    assert 'page not specified' in expand_citations('(Source 1)', [{'section': 'Source 1 — Tutorial 1 › Overview'}])
    code = '```text\n(Source 1)\n``` and `(Source 2)`'
    assert expand_citations(code, SOURCES) == code
    assert expand_citations('$x^2$ (Source 1)', SOURCES).startswith('$x^2$ ')


def test_saved_localized_metadata_and_markdown_file_names():
    sources = [{'section': 'מטלה 1 — HW_3_ALGO.pdf, Problem 2, PDF pages 1, 2'}]
    shown = expand_citations('(Assignment 1)', sources, 'he')
    assert 'מטלה 3' in shown
    assert 'עמודים 1, 2' in shown


def test_lecture_label_and_no_section_titles():
    sources = [{'section': 'Source 1 — Lecture 4 — Dynamic Programming › Examples — PDF pages 10–12'}]
    assert expand_citations('(Source 1)', sources) == '(Lecture 4 — pages 10–12)'
    assert expand_citations('(Source 1)', sources, 'he') == '(הרצאה 4 — עמודים 10–12)'
