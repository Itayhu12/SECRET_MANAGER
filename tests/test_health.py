"""
tests/test_health.py
--------------------
Smoke test: confirms the app factory boots and /health responds.
Run with: pytest tests/ -v
"""

import pytest
from app import create_app
from config import TestingConfig


@pytest.fixture
def client():
    app = create_app(config_class=TestingConfig)
    with app.test_client() as c:
        yield c


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
