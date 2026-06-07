from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


class SessionReportRow(Base):
    __tablename__ = "session_reports"

    session_id: Mapped[str] = mapped_column(String, primary_key=True)
    transcript_path: Mapped[str] = mapped_column(String)
    project_path: Mapped[str | None] = mapped_column(String, nullable=True)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    analyzed_at: Mapped[datetime] = mapped_column(DateTime)
    report_json: Mapped[dict] = mapped_column(JSON)
    upload_id: Mapped[str | None] = mapped_column(String, nullable=True)


class UploadRow(Base):
    __tablename__ = "uploads"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    session_count: Mapped[int] = mapped_column(Integer)
    project_paths: Mapped[list] = mapped_column(JSON)
    session_ids: Mapped[list] = mapped_column(JSON)
    pipeline_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class ProfileRow(Base):
    __tablename__ = "profile_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime)
    profile_json: Mapped[dict] = mapped_column(JSON)


class ProcessingJobRow(Base):
    __tablename__ = "processing_jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    status: Mapped[str] = mapped_column(String, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)
    force: Mapped[bool] = mapped_column(Boolean, default=False)
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    succeeded: Mapped[int] = mapped_column(Integer, default=0)
    failed: Mapped[int] = mapped_column(Integer, default=0)
    current_file: Mapped[str | None] = mapped_column(String, nullable=True)
    current_step: Mapped[str | None] = mapped_column(String, nullable=True)
    results_json: Mapped[list] = mapped_column(JSON, default=list)
    upload_id: Mapped[str | None] = mapped_column(String, nullable=True)
    logs_json: Mapped[list] = mapped_column(JSON, default=list)
    openai_calls_json: Mapped[list] = mapped_column(JSON, default=list)


def make_engine(db_path: str):
    return create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})


def _migrate_schema(engine) -> None:
    insp = inspect(engine)
    if "processing_jobs" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("processing_jobs")}
        if "openai_calls_json" not in cols:
            with engine.begin() as conn:
                conn.execute(
                    text("ALTER TABLE processing_jobs ADD COLUMN openai_calls_json JSON DEFAULT '[]'")
                )
    if "uploads" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("uploads")}
        if "pipeline_json" not in cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE uploads ADD COLUMN pipeline_json JSON"))


def init_db(engine) -> sessionmaker:
    Base.metadata.create_all(engine)
    _migrate_schema(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
