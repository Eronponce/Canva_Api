from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SoftDeleteMixin:
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Course(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_ref: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    canvas_course_id: Mapped[int | None] = mapped_column(Integer, index=True)
    course_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    course_code: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    term_name: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    workflow_state: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), default="manual", nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    group_links: Mapped[list["GroupCourse"]] = relationship(back_populates="course")
    job_targets: Mapped[list["JobTargetCourse"]] = relationship(back_populates="course")
    job_results: Mapped[list["JobCourseResult"]] = relationship(back_populates="course")


class CourseGroup(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "course_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(12), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(180), nullable=False, unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)

    course_links: Mapped[list["GroupCourse"]] = relationship(back_populates="group")
    job_targets: Mapped[list["JobTargetGroup"]] = relationship(back_populates="group")


class GroupCourse(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "group_courses"
    __table_args__ = (UniqueConstraint("group_id", "course_id", name="uq_group_course"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("course_groups.id"), nullable=False, index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False, index=True)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    added_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    group: Mapped["CourseGroup"] = relationship(back_populates="course_links")
    course: Mapped["Course"] = relationship(back_populates="group_links")


class JobRun(Base):
    __tablename__ = "job_runs"
    __table_args__ = (Index("ix_job_runs_kind_created", "kind", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(12), nullable=False, unique=True, index=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    base_url: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    canvas_user_id: Mapped[int | None] = mapped_column(Integer, index=True)
    canvas_user_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    request_token_source: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    request_payload_json: Mapped[dict | None] = mapped_column(JSON)
    summary_json: Mapped[dict | None] = mapped_column(JSON)
    result_json: Mapped[dict | None] = mapped_column(JSON)
    error_message: Mapped[str | None] = mapped_column(Text)
    report_filename: Mapped[str | None] = mapped_column(String(255))
    requested_strategy: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    effective_strategy: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    dry_run: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    dedupe: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    progress_current: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    progress_total: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    progress_percent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    progress_step: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    logs: Mapped[list["JobLog"]] = relationship(back_populates="job_run")
    target_groups: Mapped[list["JobTargetGroup"]] = relationship(back_populates="job_run")
    target_courses: Mapped[list["JobTargetCourse"]] = relationship(back_populates="job_run")
    course_results: Mapped[list["JobCourseResult"]] = relationship(back_populates="job_run")


class JobLog(Base):
    __tablename__ = "job_logs"
    __table_args__ = (Index("ix_job_logs_job_created", "job_run_id", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_run_id: Mapped[int] = mapped_column(ForeignKey("job_runs.id"), nullable=False, index=True)
    level: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    data_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    job_run: Mapped["JobRun"] = relationship(back_populates="logs")


class JobTargetGroup(Base):
    __tablename__ = "job_target_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_run_id: Mapped[int] = mapped_column(ForeignKey("job_runs.id"), nullable=False, index=True)
    group_id: Mapped[int | None] = mapped_column(ForeignKey("course_groups.id"), index=True)
    group_public_id: Mapped[str] = mapped_column(String(12), default="", nullable=False)
    group_name_snapshot: Mapped[str] = mapped_column(String(180), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    job_run: Mapped["JobRun"] = relationship(back_populates="target_groups")
    group: Mapped["CourseGroup"] = relationship(back_populates="job_targets")


class JobTargetCourse(Base):
    __tablename__ = "job_target_courses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_run_id: Mapped[int] = mapped_column(ForeignKey("job_runs.id"), nullable=False, index=True)
    course_id: Mapped[int | None] = mapped_column(ForeignKey("courses.id"), index=True)
    course_ref_snapshot: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    course_name_snapshot: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    job_run: Mapped["JobRun"] = relationship(back_populates="target_courses")
    course: Mapped["Course"] = relationship(back_populates="job_targets")


class JobCourseResult(Base):
    __tablename__ = "job_course_results"
    __table_args__ = (Index("ix_job_course_results_job_status", "job_run_id", "status"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_run_id: Mapped[int] = mapped_column(ForeignKey("job_runs.id"), nullable=False, index=True)
    course_id: Mapped[int | None] = mapped_column(ForeignKey("courses.id"), index=True)
    course_ref_snapshot: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    course_name_snapshot: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False, index=True)
    strategy_requested: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    strategy_used: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    students_found: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    manual_matches: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duplicates_skipped: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    recipients_targeted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    recipients_sent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    batch_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    announcement_id: Mapped[int | None] = mapped_column(Integer, index=True)
    announcement_url: Mapped[str | None] = mapped_column(String(500))
    conversation_ids_json: Mapped[list | None] = mapped_column(JSON)
    published: Mapped[bool | None] = mapped_column(Boolean)
    delayed_post_at: Mapped[str | None] = mapped_column(String(64))
    dry_run: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    messageable_context: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    manual_recipients: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    raw_result_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    job_run: Mapped["JobRun"] = relationship(back_populates="course_results")
    course: Mapped["Course"] = relationship(back_populates="job_results")
