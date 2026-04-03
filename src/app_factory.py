from __future__ import annotations

from flask import Flask

from src.config import AppConfig
from src.database import Base, CourseRepository, DatabaseAdminRepository, DatabaseManager, GroupRepository, JobRepository, ReportRepository
from src.database.legacy_import import LegacyJsonImportService
from src.domain.announcement_service import AnnouncementService
from src.domain.connection_service import ConnectionService
from src.domain.course_service import CourseService
from src.domain.env_service import EnvService
from src.domain.message_service import MessageService
from src.jobs.job_manager import JobManager
from src.logging_setup import configure_logging
from src.web.routes import register_error_handlers, web


def create_app() -> Flask:
    app_config = AppConfig.from_env()
    app_config.ensure_runtime_dirs()
    configure_logging(app_config)

    app = Flask(
        __name__,
        template_folder=str(app_config.templates_dir),
        static_folder=str(app_config.static_dir),
    )
    app.config["APP_CONFIG"] = app_config

    database = DatabaseManager(app_config.database_url, echo=app_config.database_echo)
    database.create_all(Base.metadata)

    course_repository = CourseRepository(database)
    group_repository = GroupRepository(database)
    job_repository = JobRepository(database)
    report_repository = ReportRepository(database)
    database_admin_repository = DatabaseAdminRepository(database)

    legacy_import_service = LegacyJsonImportService(
        app_config,
        course_repository,
        group_repository,
        job_repository,
    )
    if app_config.legacy_json_import_enabled:
        legacy_import_service.import_if_needed()

    job_manager = JobManager(job_repository, history_limit=app_config.history_limit)
    connection_service = ConnectionService(app_config)
    course_service = CourseService(connection_service, group_repository, course_repository)
    env_service = EnvService(app_config)
    announcement_service = AnnouncementService(app_config, connection_service, job_manager)
    message_service = MessageService(app_config, connection_service, job_manager)

    app.extensions["services"] = {
        "database": database,
        "database_admin_repository": database_admin_repository,
        "job_manager": job_manager,
        "job_repository": job_repository,
        "report_repository": report_repository,
        "connection_service": connection_service,
        "course_service": course_service,
        "env_service": env_service,
        "announcement_service": announcement_service,
        "message_service": message_service,
    }

    app.register_blueprint(web)
    register_error_handlers(app)
    return app
