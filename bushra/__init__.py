import logging
import os
from logging.handlers import RotatingFileHandler

from flask import Flask, has_request_context

from .config import DevelopmentConfig
from .modals import db, migrate
from .modals.branches_db import Branch, BranchClasses
from .modules import admin_bp, auth_bp, main_bp
from .modals.staff_db import Teacher 

from flask_login import LoginManager, current_user
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = "warning"


@login_manager.user_loader
def load_user(user_id):
    """
    Flask-Login callback to reload the user object from the user ID stored in session.
    """
    return Teacher.query.get(int(user_id))



# create app instant
def create_app():
    app = Flask(__name__, template_folder="templates")

    app.config.from_object(DevelopmentConfig)

    # register all blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(main_bp)

    db.init_app(app)
    migrate.init_app(app, db)

    @app.context_processor
    def inject_branch_scope():
        from .modules.admin.utils.branch_utils import (
            locked_branch_id,
            user_can_select_branch,
        )

        if not has_request_context():
            return {"can_select_branch": False, "locked_branch_id": None}

        return {
            "can_select_branch": user_can_select_branch(),
            "locked_branch_id": locked_branch_id(),
        }

    @app.context_processor
    def inject_branch_data():
        from .modules.admin.utils.subscription import subscription_for_branch

        if not has_request_context() or not getattr(
            current_user, "is_authenticated", False
        ):
            return {}

        if current_user.is_super_admin:
            return {"target_branch_info": None, "subscription": None}

        branch = Branch.query.get(current_user.branch_id)
        show_sub = bool(branch and getattr(current_user, "is_admin", False))

        return {
            "target_branch_info": branch,
            "subscription": subscription_for_branch(branch) if show_sub else None,
        }

    if not os.path.exists("logs"):
        os.mkdir("logs")

    # Rotating file handler: 10MB per file, keep last 5 files
    file_handler = RotatingFileHandler(
        "logs/error.log", maxBytes=10 * 1024 * 1024, backupCount=5
    )
    file_handler.setLevel(logging.ERROR)

    # Logging format
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]"
    )
    file_handler.setFormatter(formatter)

    # Add handler to Flask app logger
    app.logger.addHandler(file_handler)

    # Optional: log to console during development
    if app.config.get("DEBUG"):
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        app.logger.addHandler(console_handler)

    app.logger.setLevel(logging.INFO)
    app.logger.info("App startup")

    login_manager.init_app(app)


    return app
