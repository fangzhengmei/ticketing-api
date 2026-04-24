import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from main import app
from app.database import get_db
from app.database import Base
from app.auth import UserRole

TEST_DB_URL = "sqlite+pysqlite:///:memory:"

TEST_API_KEYS = {
    "test-user-key-1": {"user_id": "user-123", "role": UserRole.user},
    "test-user-key-2": {"user_id": "user-456", "role": UserRole.user},
    "test-user-key-3": {"user_id": "user-creator", "role": UserRole.user},
    "test-user-key-4": {"user_id": "user-other", "role": UserRole.user},
    "test-admin-key-1": {"user_id": "admin-001", "role": UserRole.admin},
}


def get_env_api_keys():
    parts = []
    for key, info in TEST_API_KEYS.items():
        parts.append(f"{key}:{info['user_id']}:{info['role'].value}")
    return ",".join(parts)


engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function", autouse=True)
def set_test_env():
    original_api_keys = os.environ.get("API_KEYS")
    os.environ["API_KEYS"] = get_env_api_keys()
    yield
    if original_api_keys is not None:
        os.environ["API_KEYS"] = original_api_keys
    else:
        os.environ.pop("API_KEYS", None)


@pytest.fixture(scope="function")
def client():
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def auth_headers(api_key: str) -> dict:
    return {"Authorization": f"Bearer {api_key}"}


def user_headers(user_key: str = "test-user-key-1") -> dict:
    return auth_headers(user_key)


def admin_headers() -> dict:
    return auth_headers("test-admin-key-1")
