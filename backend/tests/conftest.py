import os
import tempfile

import pytest
from sqlmodel import SQLModel

_db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_db_file.name}"
os.environ["UPLOAD_DIR"] = tempfile.mkdtemp()


@pytest.fixture(autouse=True)
def reset_db():
    from app.db.session import create_db_and_tables, engine

    SQLModel.metadata.drop_all(engine)
    create_db_and_tables()


@pytest.fixture
def session():
    from app.db.session import engine
    from sqlmodel import Session

    with Session(engine) as s:
        yield s
