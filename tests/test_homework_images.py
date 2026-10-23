"""Question boundaries must preserve PDF artwork and multi-page subsections."""
import pymupdf
from homework_images import question_images, question_regions
import rag_engine as rag


def test_all_actual_questions_render_as_png_and_exclude_neighbors():
    for hw in rag.load_homework().values():
        path = rag.HERE / hw['problem_pdf']
        with pymupdf.open(path) as document:
            for statement in hw['problem_statements']:
                images = question_images(hw, statement)
                assert [i['page'] for i in images] == statement['pages']
                assert all(i['png'].startswith(b'\x89PNG\r\n\x1a\n') and i['cropped'] for i in images)
                regions = question_regions(document, statement['number'], tuple(statement['pages']))
                text = '\n'.join(document[p - 1].get_text(clip=clip) for p, clip, _ in regions)
                assert f"Problem {statement['number']}" in text
                assert f"Problem {statement['number'] + 1}" not in text
                assert f"Problem {statement['number'] - 1}" not in text


def test_question_continuation_and_fallback(tmp_path):
    path = tmp_path / 'two-pages.pdf'
    with pymupdf.open() as doc:
        page = doc.new_page()
        page.insert_text((50, 60), 'Problem 1:')
        page.insert_text((50, 100), '(a) First part')
        page = doc.new_page()
        page.insert_text((50, 60), '(b) Continued proof and diagram')
        page.insert_text((50, 160), 'Problem 2:')
        doc.save(path)
    with pymupdf.open(path) as doc:
        regions = question_regions(doc, 1, (1, 2))
        assert len(regions) == 2
        assert '(b) Continued proof' in doc[1].get_text(clip=regions[1][1])
        assert 'Problem 2' not in doc[1].get_text(clip=regions[1][1])
        fallback = question_regions(doc, 99, (1,))
        assert not fallback[0][2]
        assert fallback[0][1] == doc[0].rect


def test_reported_last_question_excludes_footer_and_preserves_original():
    hw = rag.load_homework()['hw_1']
    statement = hw['problem_statements'][4]
    with pymupdf.open(rag.HERE / hw['problem_pdf']) as doc:
        _, clip, cropped = question_regions(doc, 5, (3,))[0]
        assert cropped
        assert clip.height < 180
        assert clip.y1 < 450  # Question ends well above the page-number footer.
        assert 'FALSE' in doc[2].get_text(clip=clip)
    compact = question_images(hw, statement)[0]
    original = question_images(hw, statement, original=True)[0]
    assert not original['cropped']
    assert compact['png'] != original['png']
    with pymupdf.open(stream=original['png'], filetype='png') as doc:
        assert doc[0].rect.height > doc[0].rect.width


def test_diagram_below_text_is_retained_when_removing_footer(tmp_path):
    path = tmp_path / 'diagram.pdf'
    with pymupdf.open() as doc:
        page = doc.new_page(width=612, height=792)
        page.insert_text((130, 100), 'Problem 1:')
        page.insert_text((130, 130), 'Explain this graph:')
        page.draw_rect(pymupdf.Rect(140, 180, 320, 320))
        page.insert_text((304, 700), '1')
        doc.save(path)
    with pymupdf.open(path) as doc:
        _, clip, _ = question_regions(doc, 1, (1,))[0]
        assert clip.y1 > 320
        assert clip.y1 < 400
