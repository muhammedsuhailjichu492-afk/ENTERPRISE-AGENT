
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_tmp_dir = tempfile.mkdtemp(prefix="enterprise_agent_test_")
os.environ["DATABASE_PATH"] = str(Path(_tmp_dir) / "test.db")
os.environ["CHROMA_PATH"] = str(Path(_tmp_dir) / "chroma")
os.environ.pop("ANTHROPIC_API_KEY", None)  # force offline stub for deterministic tests

import pytest


@pytest.fixture(scope="session", autouse=True)
def _init_test_environment():
    from app.database import init_db, seed_sample_data
    from app import vector_store

    init_db()
    seed_sample_data()
    vector_store.seed_if_empty()
    yield
