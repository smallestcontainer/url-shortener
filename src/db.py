from datetime import datetime

from sqlalchemy import BigInteger, Engine, Integer, String, create_engine, func, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

URL_MAX_LENGTH = 2083

MAX_ID = 2**63 - 1

_SCHEMA_LOCK_ID = 0x5E0127


class Base(DeclarativeBase):
    pass


class Link(Base):
    __tablename__ = "links"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True
    )
    url: Mapped[str] = mapped_column(String(URL_MAX_LENGTH), unique=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


def make_engine(url: str) -> Engine:
    return create_engine(url, pool_pre_ping=True)


def init_db(engine: Engine) -> None:
    with engine.begin() as conn:
        if conn.dialect.name == "postgresql":
            conn.execute(
                text("SELECT pg_advisory_xact_lock(:id)"), {"id": _SCHEMA_LOCK_ID}
            )
        Base.metadata.create_all(conn)
