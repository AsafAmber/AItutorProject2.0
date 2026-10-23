import pytest

from math_rendering import fix_math


@pytest.mark.parametrize('text,expected', [
    (r'Cost \(O(n \log n)\).', r'Cost $O(n \log n)$.'),
    (r'\[\frac{n(n-1)}{2}\]', '\n\n$$\n' + r'\frac{n(n-1)}{2}' + '\n$$\n\n'),
    (r'זמן ריצה \(O(n^2)\)', r'זמן ריצה $O(n^2)$'),
    (r'Use `n^{1.3}` and `\log_2 n`.', r'Use $n^{1.3}$ and $\log_2 n$.'),
    ('Call `find_path(graph)`.', 'Call `find_path(graph)`.'),
    (r'Keep `C:\new\file`.', r'Keep `C:\new\file`.'),
    ('$a_1 \\leq b$\n\n$$x^2$$', '$a_1 \\leq b$\n\n$$x^2$$'),
])
def test_delimiters_and_idempotence(text, expected):
    assert fix_math(text) == expected
    assert fix_math(expected) == expected


@pytest.mark.parametrize('fence', ['```', '~~~'])
def test_code_fences_stay_literal(fence):
    code = fence + 'python\nprint(r"\\[x^2\\]")\n# `n^2`\n' + fence + '\n'
    assert fix_math(code + r'Outside \(x^2\)') == code + 'Outside $x^2$'
    unfinished = fence + 'python\nprint(r"\\[x^2\\]")'
    assert fix_math(unfinished) == unfinished
