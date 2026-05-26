import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


DB_PATH = Path("/private/tmp/rythm-music-analys-api-test.db")
DB_PATH.unlink(missing_ok=True)
os.environ["AUDIO_DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["AUDIO_AUTO_CREATE_TABLES"] = "true"
os.environ["AUDIO_JWT_SECRET_KEY"] = "test-secret-key-with-required-length"
os.environ["AUDIO_UPLOAD_DIR"] = "/private/tmp/rythm-music-analys-test-uploads"

from app.main import app


@pytest.fixture(scope="session")
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client
