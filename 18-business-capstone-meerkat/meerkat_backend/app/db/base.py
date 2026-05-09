from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class LiveSession(Base):
    __tablename__ = "live_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    owncast_stream_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50))
    scheduled_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_product_id: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    page_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    script_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class LiveSessionProduct(Base):
    __tablename__ = "live_session_products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("live_sessions.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    display_order: Mapped[int] = mapped_column(Integer)
    anchor_alias: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SkuInventory(Base):
    __tablename__ = "sku_inventory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    sku_name: Mapped[str] = mapped_column(String(200))
    available_stock: Mapped[int] = mapped_column(Integer)
    locked_stock: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Coupon(Base):
    __tablename__ = "coupons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_coupon_id: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    threshold_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(50))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    applicable_product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class OwncastEvent(Base):
    __tablename__ = "owncast_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_type: Mapped[str] = mapped_column(String(100))
    raw_payload_json: Mapped[str] = mapped_column(Text)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class LiveComment(Base):
    __tablename__ = "live_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("live_sessions.id"))
    owncast_event_id: Mapped[int | None] = mapped_column(ForeignKey("owncast_events.id"), nullable=True)
    external_message_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    user_name: Mapped[str] = mapped_column(String(100))
    user_external_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    body: Mapped[str] = mapped_column(Text)
    normalized_body: Mapped[str] = mapped_column(Text)
    matched_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class OpsAlert(Base):
    __tablename__ = "ops_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("live_sessions.id"))
    alert_type: Mapped[str] = mapped_column(String(50))
    severity: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(300))
    summary: Mapped[str] = mapped_column(Text)
    evidence_json: Mapped[str] = mapped_column(Text)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    coupon_id: Mapped[int | None] = mapped_column(ForeignKey("coupons.id"), nullable=True)
    dedupe_key: Mapped[str] = mapped_column(String(300), unique=True)
    created_by: Mapped[str] = mapped_column(String(50))
    trace_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class SpeakerNote(Base):
    __tablename__ = "speaker_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("live_sessions.id"))
    alert_id: Mapped[int | None] = mapped_column(ForeignKey("ops_alerts.id"), nullable=True)
    body: Mapped[str] = mapped_column(Text)
    target: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(50))
    created_by: Mapped[str] = mapped_column(String(50))
    trace_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ActionProposal(Base):
    __tablename__ = "action_proposals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("live_sessions.id"))
    alert_id: Mapped[int | None] = mapped_column(ForeignKey("ops_alerts.id"), nullable=True)
    action_type: Mapped[str] = mapped_column(String(100))
    risk_level: Mapped[str] = mapped_column(String(50))
    arguments_json: Mapped[str] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50))
    created_by_agent: Mapped[str] = mapped_column(String(100))
    trace_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ApprovalTask(Base):
    __tablename__ = "approval_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    proposal_id: Mapped[int | None] = mapped_column(ForeignKey("action_proposals.id"), nullable=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("live_sessions.id"))
    risk_level: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(300))
    reason: Mapped[str] = mapped_column(Text)
    payload_json: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50))
    reviewer: Mapped[str | None] = mapped_column(String(100), nullable=True)
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AgentTask(Base):
    __tablename__ = "agent_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trace_id: Mapped[str] = mapped_column(String(100), unique=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("live_sessions.id"))
    task_type: Mapped[str] = mapped_column(String(100))
    source: Mapped[str] = mapped_column(String(100))
    alert_type_hint: Mapped[str | None] = mapped_column(String(50), nullable=True)
    comment_ids_json: Mapped[str] = mapped_column(Text)
    input_payload_json: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("agent_tasks.id"))
    trace_id: Mapped[str] = mapped_column(String(100))
    root_agent: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(50))
    final_output_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AgentActionLog(Base):
    __tablename__ = "agent_action_logs"
    __table_args__ = (UniqueConstraint("trace_id", "id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trace_id: Mapped[str] = mapped_column(String(100))
    session_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    agent_name: Mapped[str] = mapped_column(String(100))
    parent_agent_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    action_type: Mapped[str] = mapped_column(String(100))
    tool_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    input_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(50))
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
