"""Expand validated source IDs for readers without changing model-facing citations."""
from __future__ import annotations

import re

from rag_engine import _CITATION_RE, split_grouped_citations

_LABEL = re.compile(r'^(Source|Assignment|מקור|מטלה|משימה)\s+(\d+)\s+[—–-]\s+(.+)$', re.I | re.S)
_REFERENCE = re.compile(_CITATION_RE.pattern + r'|(?<!\w)(Source|Assignment|מקור|מטלה|משימה)\s+(\d+)\b', re.I)
_CODE = re.compile(r'(```[\s\S]*?```|~~~[\s\S]*?~~~|`[^`\n]*`)')


def _kind(label: str) -> str:
    return 'source' if label.casefold() in ('source', 'מקור') else 'assignment'


def _short_label(description: str, kind: str, language: str) -> str:
    identity = re.search(r'\b(Tutorial|Lecture|Homework|Assignment)[ _-]+(\d+)\b|'
                         r'(תרגול|הרצאה|מטלה)\s+(\d+)', description, re.I)
    names = {'tutorial': ('Tutorial', 'תרגול'), 'lecture': ('Lecture', 'הרצאה'),
             'homework': ('Homework', 'מטלה'), 'assignment': ('Homework', 'מטלה'),
             'תרגול': ('Tutorial', 'תרגול'), 'הרצאה': ('Lecture', 'הרצאה'),
             'מטלה': ('Homework', 'מטלה')}
    he = language == 'he'
    if identity:
        source_type = (identity[1] or identity[3]).casefold()
        title = names[source_type][he] + ' ' + (identity[2] or identity[4])
    else:
        hw = re.search(r'\bHW[_ -]?(\d+)', description, re.I) if _kind(kind) == 'assignment' else None
        title = (('מטלה ' if he else 'Homework ') + hw[1] if hw else
                 ('חומר הקורס' if he else 'Course material'))
    page = re.search(r'(?:PDF\s+pages?|slides?|עמודי?\s+PDF|עמודים|עמוד)\s*:?\s*'
                     r'(\d+(?:\s*[–—-]\s*\d+)?(?:\s*,\s*\d+(?:\s*[–—-]\s*\d+)?)*)',
                     description, re.I)
    if page:
        title += ' — ' + ('עמודים ' if he else 'pages ') + page[1]
    else:
        title += ' — ' + ('עמוד לא צוין במקור' if he else 'page not specified')
    return title


def expand_citations(text: str, sources: list[dict], language: str = 'en') -> str:
    """Only resolve IDs using this answer's original retrieved-source metadata."""
    labels = {}
    for source in sources:
        match = _LABEL.match(source.get('section', ''))
        if not match:
            continue
        kind, number, description = match.groups()
        description = _short_label(description, kind, language)
        labels[(_kind(kind), int(number))] = description

    def replace(match):
        kind = match[1] or match[3]
        number = match[2] or match[4]
        description = labels.get((_kind(kind), int(number)))
        if description is None:
            return match[0]
        return '(' + description + ')' if match[1] else description

    pieces = _CODE.split(text)
    return ''.join(piece if i % 2 else _REFERENCE.sub(replace, split_grouped_citations(piece))
                   for i, piece in enumerate(pieces))
