from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


settings = get_settings()

engine = create_engine(
    settings.normalized_database_url(),
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_lightweight_migrations()


def ensure_lightweight_migrations() -> None:
    inspector = inspect(engine)
    if "meetings" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("meetings")}
    statements = []
    if "report_type" not in columns:
        statements.append("ALTER TABLE meetings ADD COLUMN report_type VARCHAR(50) NOT NULL DEFAULT 'meeting'")
    if "custom_prompt" not in columns:
        statements.append("ALTER TABLE meetings ADD COLUMN custom_prompt TEXT")
    if "image_file_paths" not in columns:
        statements.append("ALTER TABLE meetings ADD COLUMN image_file_paths TEXT")
    if "image_context" not in columns:
        statements.append("ALTER TABLE meetings ADD COLUMN image_context TEXT")

    if not statements:
        return

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
