"""The learning catalog is complete, source-backed, read-only, and local."""
from fastapi.testclient import TestClient
from backend.catalog import load_catalog
from backend.main import create_app


def test_learning_catalog_preserves_every_original_and_does_not_create_history(tmp_path):
    catalog = load_catalog()
    app = create_app(db_path=tmp_path / 'learning.sqlite3', catalog=catalog)
    with TestClient(app) as client:
        response = client.get('/api/hexagrams')
        assert response.status_code == 200
        summaries = response.json()
        assert [entry['wenwang_order'] for entry in summaries] == list(range(1, 65))
        assert len({entry['binary_code'] for entry in summaries}) == 64
        for summary in summaries:
            original = catalog.get(summary['wenwang_order'])
            assert summary == {key: original[key] for key in summary}
            assert 'line_texts' not in summary
            detail = client.get(f"/api/hexagrams/{summary['wenwang_order']}")
            assert detail.status_code == 200
            for key in ('title', 'binary_code', 'judgment', 'line_texts', 'source_url', 'source_revision_id'):
                assert detail.json()[key] == original[key]
            assert detail.json()['special_line'] == original.get('special_line')
        assert client.get('/api/history').json() == {'items': [], 'total': 0}
        for invalid in (0, 65):
            assert client.get(f'/api/hexagrams/{invalid}').status_code == 404


def test_learning_directory_uses_injected_catalog_and_keeps_desktop_auth(tmp_path):
    catalog = load_catalog()
    catalog.get(1)['title'] = '测试目录唯一来源'
    app = create_app(db_path=tmp_path / 'desktop.sqlite3', catalog=catalog,
                     desktop_mode=True, desktop_api_token='test-learning-token')
    with TestClient(app) as client:
        assert client.get('/api/hexagrams').status_code == 401
        response = client.get('/api/hexagrams', headers={'Authorization': 'Bearer test-learning-token'})
        assert response.status_code == 200
        assert response.json()[0]['title'] == '测试目录唯一来源'
