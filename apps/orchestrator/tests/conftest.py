"""Existing tests write seed records; keep every test away from the user's data."""
import os
import tempfile
from pathlib import Path
import pytest

_test_data = tempfile.TemporaryDirectory(prefix="amani-tests-")
os.environ["AMANI_DATA_DIR"] = _test_data.name
os.environ["AMANI_LEGACY_DB"] = str(Path(_test_data.name) / "legacy.db")
os.environ["DATABASE_URL"] = ""
os.environ["ADMIN_API_TOKEN"] = "test-moderator-token-with-enough-entropy"
os.environ["OPENAI_API_KEY"] = ""
os.environ["LLM_API_KEY"] = ""
os.environ["APP_ENV"] = "test"

@pytest.fixture(autouse=True)
def isolate_legacy_store(tmp_path, monkeypatch):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    import main
    monkeypatch.setattr(main, "DB_PATH", tmp_path / "legacy.db")
    main.initialize_database()
