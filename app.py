"""
app.py — Flask factory.
يُسجِّل البلوبرنتات ويُعيد تطبيق Flask جاهزاً.
"""
from flask import Flask
from config import Config


def create_app() -> Flask:
    app = Flask(__name__, template_folder='dashboard/templates')
    app.secret_key = Config.SECRET_KEY

    # ── تسجيل البلوبرنتات ────────────────────────────────────────────────────
    from dashboard.blueprints.auth    import auth_bp
    from dashboard.blueprints.main_bp import main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    return app
