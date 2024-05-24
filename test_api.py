import json
from .main import create_app


def mock_fetch_data():
    return {}

def test_import_app():
    app = create_app(mock_fetch_data)

    with app.test_client() as test_client:
        test_client = app.test_client()
        res = test_client.get('/api')
        data = res.text
        assert json.loads(data) == {}
        assert res.status_code == 200
