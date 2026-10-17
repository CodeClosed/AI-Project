import os
import tempfile
import pytest

# Point DATABASE_URL to an isolated temporary SQLite database before application modules load
_temp_db_fd, temp_db_path = tempfile.mkstemp(prefix="test_nutrimenu_", suffix=".db")
os.close(_temp_db_fd)
os.environ["DATABASE_URL"] = f"sqlite:///{temp_db_path}"

@pytest.fixture(scope="session", autouse=True)
def isolated_test_database():
    from backend.database import init_db, engine
    init_db()
    yield
    try:
        engine.dispose()
        if os.path.exists(temp_db_path):
            os.remove(temp_db_path)
    except Exception:
        pass
