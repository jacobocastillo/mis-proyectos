"""
Application factory module for the StreakUP Flask backend.

Responsibility:
- Create and configure the Flask application instance.
- Initialize shared extensions and register blueprints.
"""

from flask import Flask
from flask_cors import CORS

from .cli import register_cli_commands
from .config import Config, get_cors_origins, validate_runtime_secrets
from .extensions import init_extensions


def create_app(config_class: type[Config] = Config) -> Flask:
    """Create and configure the Flask application instance."""
    app = Flask(__name__)
    app.config.from_object(config_class)
    validate_runtime_secrets(app.config)

    cors_origins = get_cors_origins(app.config)
    if cors_origins:
        CORS(
            app,
            resources={
                r"/api/*": {
                    "origins": "*" if cors_origins == ("*",) else list(cors_origins),
                    "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                    "allow_headers": ["Content-Type", "Authorization"],
                }
            },
        )

    init_extensions(app)
    register_cli_commands(app)

    from app.routes.auth_routes import auth_bp
    from app.routes.habit_routes import habits_bp
    from app.routes.ops_routes import ops_bp
    from app.routes.checkin_routes import checkins_bp
    from app.routes.stats_routes import stats_bp
    from app.routes.pomodoro_routes import pomodoro_bp
    from app.routes.validation_routes import validation_bp
    from app.routes.achievement_routes import achievements_bp
    from app.routes.user_routes import user_bp
    from app.routes.social_routes import social_bp
    from app.routes.sync_routes import sync_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(habits_bp, url_prefix="/api")
    app.register_blueprint(checkins_bp, url_prefix="/api/checkins")
    app.register_blueprint(stats_bp, url_prefix="/api/stats")
    app.register_blueprint(pomodoro_bp, url_prefix="/api/pomodoro")
    app.register_blueprint(validation_bp, url_prefix="/api")
    app.register_blueprint(achievements_bp, url_prefix="/api")
    app.register_blueprint(user_bp, url_prefix="/api/users")
    app.register_blueprint(social_bp, url_prefix="/api/social")
    app.register_blueprint(sync_bp, url_prefix="/api/sync")
    app.register_blueprint(ops_bp)

    with app.app_context():
        from app.models.user import User  # noqa: F401
        from app.models.habit import Category, Habit  # noqa: F401
        from app.models.user_habit import UserHabit  # noqa: F401
        from app.models.checkin import CheckIn  # noqa: F401
        from app.models.pomodoro_session import PomodoroSession  # noqa: F401
        from app.models.validation_log import ValidationLog  # noqa: F401
        from app.models.xp_log import XpLog  # noqa: F401
        from app.models.achievement import Achievement, UserAchievement  # noqa: F401
        from app.models.user_habit_schedule import UserHabitScheduleDay  # noqa: F401
        from app.models.social import SharedStreakGroup, SharedStreakMembership  # noqa: F401
        from app.models.sync_operation import SyncOperation  # noqa: F401
        from app.models.token_blocklist import TokenBlocklist  # noqa: F401

        # Seed achievement catalog if the table exists (skipped during migrations)
        try:
            from app.services.achievement_service import seed_achievements
            seed_achievements()
        except Exception:
            pass  # Table may not exist yet during initial migration run

    return app
