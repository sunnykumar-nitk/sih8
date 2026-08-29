"""
Persistent storage via SQLAlchemy + SQLite (see config.DATABASE_URL).

Design choice for a hackathon prototype: rather than mapping every field of
a `site` dict to its own SQL column (they vary a lot: population_data is a
nested dict, breakdown is a dict, etc.), each row stores the full site/team
dict as JSON in a `data` column, keyed by its id. This keeps SITE_STORE and
TEAM_STORE (plain Python dicts, used everywhere else in the codebase) as
the single source of truth in memory, while every write is mirrored to SQL
so data survives a process restart. On startup, existing rows are loaded
back into those dicts.

This is intentionally simple -- not a full ORM data model -- because the
actual requirement being solved is "don't lose everything when the server
restarts", not "normalize disaster-assessment data into 10 SQL tables".
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

from sqlalchemy import create_engine, Column, String, Text, DateTime, func
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

# check_same_thread=False: FastAPI can serve a request on a different
# thread than the one that created the engine; SQLite needs this relaxed
# for a simple demo setup (a real deployment would use a proper pool).
_engine = create_engine(
    config.DATABASE_URL,
    connect_args={"check_same_thread": False} if config.DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)


class SiteRecord(Base):
    __tablename__ = "sites"
    site_id = Column(String, primary_key=True)
    data = Column(Text, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class TeamRecord(Base):
    __tablename__ = "teams"
    team_id = Column(String, primary_key=True)
    data = Column(Text, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ChatLogRecord(Base):
    """Optional log of chatbot Q&A -- useful for a demo/judge to show history."""
    __tablename__ = "chat_log"
    id = Column(String, primary_key=True)  # uuid, set by caller
    data = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


def init_db() -> None:
    """Create tables if they don't exist yet. Safe to call multiple times."""
    os.makedirs(os.path.dirname(config.DATABASE_URL.replace("sqlite:///", "")) or ".", exist_ok=True) \
        if config.DATABASE_URL.startswith("sqlite:///") else None
    Base.metadata.create_all(bind=_engine)


def save_site(site_id: str, site_dict: Dict[str, Any]) -> None:
    with SessionLocal() as session:
        payload = json.dumps(site_dict, default=str)
        existing = session.get(SiteRecord, site_id)
        if existing:
            existing.data = payload
        else:
            session.add(SiteRecord(site_id=site_id, data=payload))
        session.commit()


def load_all_sites() -> Dict[str, Dict[str, Any]]:
    with SessionLocal() as session:
        rows = session.query(SiteRecord).all()
        return {row.site_id: json.loads(row.data) for row in rows}


def save_team(team_id: str, team_dict: Dict[str, Any]) -> None:
    with SessionLocal() as session:
        payload = json.dumps(team_dict, default=str)
        existing = session.get(TeamRecord, team_id)
        if existing:
            existing.data = payload
        else:
            session.add(TeamRecord(team_id=team_id, data=payload))
        session.commit()


def load_all_teams() -> Dict[str, Dict[str, Any]]:
    with SessionLocal() as session:
        rows = session.query(TeamRecord).all()
        return {row.team_id: json.loads(row.data) for row in rows}


def log_chat(entry_id: str, entry: Dict[str, Any]) -> None:
    with SessionLocal() as session:
        session.add(ChatLogRecord(id=entry_id, data=json.dumps(entry, default=str)))
        session.commit()
