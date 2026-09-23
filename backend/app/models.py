from datetime import datetime
from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Template(Base):
    __tablename__ = "templates"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    object_key: Mapped[str] = mapped_column(String(512), unique=True)
    schema_version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    folder: Mapped[str] = mapped_column(String(200), default="", server_default="")
    tags_json: Mapped[str] = mapped_column(Text, default="[]", server_default="[]")
    published_version_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TemplateVersion(Base):
    __tablename__ = "template_versions"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    template_id: Mapped[str] = mapped_column(String(64), index=True)
    version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="draft", server_default="draft")
    change_summary: Mapped[str] = mapped_column(String(500), default="", server_default="")
    definition_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
