"""
SQLAlchemy models for GulfAgent.
Tables: users, tasks, usage, automations, skills, user_skills, approvals
Phase 1 scope: users, tasks, usage
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class TaskStatus(str, PyEnum):
    pending = "pending"
    running = "running"
    awaiting_approval = "awaiting_approval"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class TaskType(str, PyEnum):
    simple = "simple"
    browser = "browser"
    whatsapp = "whatsapp"
    automation = "automation"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True)  # mirrors supabase auth.users.id
    email = Column(String(255), unique=True, nullable=False)
    phone = Column(String(20), nullable=True)  # E.164 format
    full_name = Column(String(255), nullable=True)
    subscription_tier = Column(String(20), default="basic")  # basic | pro | enterprise
    subscription_status = Column(String(20), default="trial")  # trial | active | cancelled
    stripe_customer_id = Column(String(100), nullable=True)
    stripe_subscription_id = Column(String(100), nullable=True)
    preferred_language = Column(String(10), default="en")  # en | ar
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    tasks = relationship("Task", back_populates="user")
    usage_records = relationship("Usage", back_populates="user")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    prompt = Column(Text, nullable=False)
    task_type = Column(String(20), default=TaskType.simple)
    status = Column(String(30), default=TaskStatus.pending)
    result = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    tokens_used = Column(Integer, default=0)
    credits_used = Column(Integer, default=0)
    metadata = Column(JSONB, default={})  # screenshots, steps, etc.
    source = Column(String(20), default="dashboard")  # dashboard | whatsapp | api | automation
    automation_id = Column(UUID(as_uuid=True), ForeignKey("automations.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="tasks")
    approval = relationship("Approval", back_populates="task", uselist=False)


class Usage(Base):
    __tablename__ = "usage"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    year_month = Column(String(7), nullable=False)  # "2024-01"
    credits_used = Column(Integer, default=0)
    tasks_run = Column(Integer, default=0)
    credits_limit = Column(Integer, default=5000)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    user = relationship("User", back_populates="usage_records")


class Automation(Base):
    __tablename__ = "automations"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    prompt = Column(Text, nullable=False)
    cron = Column(String(100), nullable=False)
    active = Column(Boolean, default=True)
    skill_id = Column(UUID(as_uuid=True), ForeignKey("skills.id", ondelete="SET NULL"), nullable=True)
    last_run = Column(DateTime(timezone=True), nullable=True)
    next_run = Column(DateTime(timezone=True), nullable=True)
    bullmq_job_id = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Skill(Base):
    __tablename__ = "skills"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=False)  # Research | E-commerce | Government | Finance | HR
    prompt_template = Column(Text, nullable=False)
    icon = Column(String(50), nullable=True)
    default_cron = Column(String(100), nullable=True)
    credit_cost = Column(Integer, default=10)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class UserSkill(Base):
    __tablename__ = "user_skills"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    skill_id = Column(UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False)
    activated_at = Column(DateTime(timezone=True), server_default=func.now())


class Approval(Base):
    __tablename__ = "approvals"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    action_type = Column(String(50), nullable=False)  # email | form_submit | payment | file_delete
    action_payload = Column(JSONB, default={})
    decision = Column(String(10), nullable=True)  # approved | denied | timeout
    expires_at = Column(DateTime(timezone=True), nullable=False)
    decided_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    task = relationship("Task", back_populates="approval")
