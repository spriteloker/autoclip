from backend.services.studio.cold_open import (
    GoldenOpeningCandidate, analyze_golden_opening, apply_golden_opening, candidate_windows,
)
from backend.services.studio.chinese import simplified_chinese
from backend.services.studio.models import Draft, Scene
from backend.services.studio.packaging import _stamp_cues
from backend.services.studio.post_copy import build_posts


def _draft(packaging=None):
    return Draft(
        id='parent', title='拖延的大腦', hook='這是開頭', revision=3,
        scenes=[Scene(id='body', label='正文', start=0, end=20, evidence='時間與選擇')],
        packaging=packaging,
    )


def _entries():
    return [
        {'start_time': '00:00:01,000', 'end_time': '00:00:03,000', 'text': 'This is a breakthrough.'},
        {'start_time': '00:00:04,000', 'end_time': '00:00:06,000', 'text': 'It changes everything.'},
        {'start_time': '00:00:07,000', 'end_time': '00:00:12,000', 'text': 'This sentence is deliberately too long.'},
    ]


def test_candidate_windows_target_five_seconds_with_eight_second_context_limit():
    candidates = candidate_windows(_draft(), _entries())
    assert [candidate.id for candidate in candidates] == [
        'golden-0-0', 'golden-0-1', 'golden-1-1', 'golden-1-2', 'golden-2-2',
    ]
    assert candidates[0].text == 'This is a breakthrough.'
    assert candidates[1].end - candidates[1].start == 5
    assert all(2 <= candidate.end - candidate.start <= 8 for candidate in candidates)


def test_unpunctuated_chinese_cues_can_form_a_complete_context_window():
    entries = [
        {'start_time': '00:00:01,000', 'end_time': '00:00:03,000', 'text': '你以为是努力不够'},
        {'start_time': '00:00:04,000', 'end_time': '00:00:06,000', 'text': '其实是方向错了'},
    ]
    candidates = candidate_windows(_draft(), entries)
    assert [candidate.id for candidate in candidates] == ['golden-0-0', 'golden-0-1', 'golden-1-1']
    assert candidates[1].text == '你以为是努力不够 其实是方向错了'


def test_model_prefers_context_and_can_only_select_real_candidates():
    def fake_call(prompt, payload):
        assert '语境完整比短更重要' in prompt
        assert payload['target_seconds'] == 5
        assert all(candidate['id'] != 'golden-0-0' for candidate in payload['candidates'])
        assert payload['candidates'][0]['before'] == ''
        assert payload['candidates'][0]['after'] == 'This sentence is deliberately too long.'
        return {'selected': [{'id': 'golden-0-1', 'reason': '這是最強的開場'}, {'id': 'invented'}]}

    selected = analyze_golden_opening(_draft(), _entries(), fake_call)
    assert len(selected) == 1
    assert selected[0].id == 'golden-0-1'
    assert selected[0].reason == '这是最强的开场'


def test_model_rejected_candidate_is_not_shown_to_users():
    def fake_call(_prompt, _payload):
        return {'selected': [{'id': 'golden-0-1', 'reason': 'ASR错字导致语义不通，不建议采用'}]}

    assert analyze_golden_opening(_draft(), _entries(), fake_call) == []


def test_apply_forks_parent_and_prepends_scene_and_packaging_cues():
    packaging = {
        'version': 1, 'template': 'interview_zh', 'audience_language': 'zh',
        'title_lines': ['拖延的大腦'], 'cues': [
            {'start': 1, 'end': 3, 'text': 'This is a breakthrough.', 'original': ''},
            {'start': 4, 'end': 6, 'text': 'It changes everything.', 'original': ''},
        ],
    }
    parent = _draft(packaging)
    candidate = GoldenOpeningCandidate(id='golden-0-0', start=1, end=3, text='This is a breakthrough.', reason='開場有力')
    created = apply_golden_opening(parent, candidate, _entries())

    assert created.id != parent.id
    assert created.origin == 'golden-open'
    assert created.parent_draft_id == parent.id
    assert created.parent_revision == parent.revision
    assert created.scenes[0].id == 'golden-open'
    assert created.scenes[1].id == 'body'
    assert created.packaging.cues[0].text == 'This is a breakthrough.'
    assert created.packaging.cues[1].text == 'This is a breakthrough.'
    assert parent.scenes[0].id == 'body'
    assert len(parent.packaging.cues) == 2
    assert parent.title == '拖延的大脑'
    assert parent.hook == '这是开头'
    assert parent.scenes[0].evidence == '时间与选择'


def test_reselecting_replaces_opening_and_its_cues_without_stacking():
    packaging = {
        'version': 1, 'template': 'interview_zh', 'audience_language': 'zh',
        'title_lines': ['标题'], 'cues': [
            {'start': 1, 'end': 3, 'text': 'This is a breakthrough.', 'original': ''},
            {'start': 4, 'end': 6, 'text': 'It changes everything.', 'original': ''},
        ],
    }
    first = apply_golden_opening(_draft(packaging), GoldenOpeningCandidate(
        id='golden-0-0', start=1, end=3, text='This is a breakthrough.'), _entries())
    second = apply_golden_opening(first, GoldenOpeningCandidate(
        id='golden-1-1', start=4, end=6, text='It changes everything.'), _entries())

    assert second.parent_draft_id == 'parent'
    assert [scene.id for scene in second.scenes] == ['golden-open', 'body']
    assert second.scenes[0].start == 4 and second.scenes[0].end == 6
    assert [cue.text for cue in second.packaging.cues] == [
        'It changes everything.', 'This is a breakthrough.', 'It changes everything.',
    ]
    assert len(first.scenes) == 2  # the previously created draft stays unchanged
    assert candidate_windows(first, _entries())


def test_apply_rejects_changed_candidate():
    candidate = GoldenOpeningCandidate(id='golden-0-0', start=1, end=3, text='This is a breakthrough.')
    try:
        apply_golden_opening(_draft(), candidate, [_entries()[1]])
    except ValueError as error:
        assert '重新生成候选' in str(error)
    else:
        raise AssertionError('stale candidate must be rejected')


def test_simplified_chinese_output_at_post_and_packaging_boundaries():
    assert simplified_chinese('這是繁體字的大腦與時間') == '这是繁体字的大脑与时间'
    assert simplified_chinese('会社の責任者') == '会社の責任者'
    assert simplified_chinese('最高経営責任者') == '最高経営責任者'

    def fake_call(prompt, payload):
        assert '简体中文' in prompt
        return {'posts': {'douyin': {'title': '拖延的大腦', 'description': '這是完整文案', 'tags': ['學習']}}}

    post = build_posts('拖延的大腦', ['完整原话'], ['douyin'], source='TED', call=fake_call)['douyin']
    assert post == {'title': '拖延的大脑', 'description': '这是完整文案', 'tags': ['学习']}

    packaged = _stamp_cues({
        'version': 1, 'template': 'interview_zh', 'audience_language': 'zh',
        'title_lines': ['拖延的大腦'],
        'cues': [{'start': 1, 'end': 3, 'text': '這是完整的一句話。', 'original': ''}],
        'speakers': [{'at': 1, 'name': '黃仁勳', 'role': ''}],
    })
    assert packaged['title_lines'] == ['拖延的大脑']
    assert packaged['cues'][0]['text'] == '这是完整的一句话。'
    assert packaged['speakers'][0]['name'] == '黄仁勋'


def test_golden_opening_routes_read_json_body_not_query_parameters(monkeypatch):
    from fastapi import FastAPI, HTTPException
    from fastapi.testclient import TestClient
    from backend.api.v1.studio import router
    from backend.core.database import get_db

    def missing_project(*_args):
        raise HTTPException(404, '项目不存在')

    monkeypatch.setattr('backend.api.v1.studio.project_or_404', missing_project)
    app = FastAPI()
    app.include_router(router, prefix='/studio')
    app.dependency_overrides[get_db] = lambda: None
    client = TestClient(app)
    candidate = GoldenOpeningCandidate(id='golden-0-0', start=1, end=3, text='This is a breakthrough.')
    bodies = [
        {'draft': _draft().model_dump()},
        {'draft': _draft().model_dump(), 'candidate': candidate.model_dump()},
    ]
    for suffix, body in zip(('/golden-opening/analyze', '/golden-opening'), bodies):
        response = client.post(f'/studio/project{suffix}', json=body)
        assert response.status_code == 404
        assert response.json()['detail'] == '项目不存在'
