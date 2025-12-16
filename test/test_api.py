# tests/test_api.py
import json
import pytest
from app import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_plan_endpoint_basic(client):
    resp = client.get("/plan")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert isinstance(data["plan"], list)
    # campos esperados
    if data["plan"]:
        item = data["plan"][0]
        assert set(item.keys()) >= {"Asesor", "Semana", "Día", "Turno"}

def test_plan_with_opening_only_param(client):
    resp = client.get("/plan?opening_only=true&opening_advisor=Asesor_2")
    assert resp.status_code == 200
    data = resp.get_json()
    # verificar que Asesor_2 tenga Apertura
    found = [p for p in data["plan"] if p["Asesor"] == "Asesor_2"]
    assert found
    for r in found:
        assert r["Turno"] == "Apertura"
