from __future__ import annotations

from flask import Flask

from src.config import AppConfig
from src.domain.announcement_service import AnnouncementService
from src.domain.connection_service import ConnectionService
from src.domain.course_service import CourseService
from src.domain.env_service import EnvService
from src.domain.message_service import MessageService
from src.jobs.job_manager import JobManager
from src.logging_setup import configure_logging
from src.storage.group_store import GroupStore
from src.storage.history_store import HistoryStore
from src.storage.registered_course_store import RegisteredCourseStore
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

    history_store = HistoryStore(app_config.history_file, limit=app_config.history_limit)
    group_store = GroupStore(app_config.groups_file)
    registered_course_store = RegisteredCourseStore(app_config.registered_courses_file)
    job_manager = JobManager(history_store)
    connection_service = ConnectionService(app_config)
    course_service = CourseService(connection_service, group_store, registered_course_store)
    env_service = EnvService(app_config)
    announcement_service = AnnouncementService(app_config, connection_service, job_manager)
    message_service = MessageService(app_config, connection_service, job_manager)

    app.extensions["services"] = {
        "job_manager": job_manager,
        "connection_service": connection_service,
        "course_service": course_service,
        "env_service": env_service,
        "announcement_service": announcement_service,
        "message_service": message_service,
    }

    app.register_blueprint(web)
    register_error_handlers(app)
    return app
