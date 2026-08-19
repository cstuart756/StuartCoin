from fastapi.testclient import TestClient
from app.api import app, node

def test_health_and_chain():
    c=TestClient(app); assert c.get('/health').status_code==200; assert c.get('/chain').status_code==200

def test_peer_registration():
    c=TestClient(app); r=c.post('/peers',json={'url':'http://localhost:9999'}); assert r.status_code==200; assert 'http://localhost:9999' in r.json()['peers']
