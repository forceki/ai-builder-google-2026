import uuid
from typing import Any

from sqlalchemy import JSON, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models._common import IdMixin


class TraceItem(IdMixin, Base):
    """One node of the traceability map: a heat, part, weld or NDT report."""

    __tablename__ = "trace_items"
    __table_args__ = (UniqueConstraint("project_id", "kind", "key"),)

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(16))  # material | part | weld | ndt
    key: Mapped[str] = mapped_column(String(64))  # normalized id, e.g. 4A7721, P-101, W-14, UT-0331
    label: Mapped[str] = mapped_column(String(120))
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    sources: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)


class TraceLink(IdMixin, Base):
    __tablename__ = "trace_links"

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    from_item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("trace_items.id", ondelete="CASCADE"))
    to_item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("trace_items.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(16), default="link")  # link | conflict
