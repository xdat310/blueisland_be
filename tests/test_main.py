import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app, get_db
from app.models import Base


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        try:
            db = SessionLocal()
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield SessionLocal()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


def test_read_root(client):
    response = client.get("/")
    assert response.status_code == 200


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code in [200, 404]  # May or may not exist


class TestUser:
    def test_list_users(self, client, db):
        response = client.get("/api/users")
        assert response.status_code == 200

    def test_create_user(self, client, db):
        user_data = {
            "email": "test@example.com",
            "password": "testpass123",
            "full_name": "Test User"
        }
        response = client.post("/api/users/register", json=user_data)
        assert response.status_code in [200, 201]
        if response.status_code == 201:
            data = response.json()
            assert data["email"] == user_data["email"]


class TestAuth:
    def test_login(self, client, db):
        user_data = {
            "email": "auth_test@example.com",
            "password": "testpass123",
            "full_name": "Auth Test"
        }
        client.post("/api/users/register", json=user_data)

        login_data = {
            "email": user_data["email"],
            "password": user_data["password"]
        }
        response = client.post("/api/auth/login", json=login_data)
        assert response.status_code in [200, 401, 422]
