import os

basedir = os.path.abspath(os.path.dirname(__file__))  # points to bushra/


class Config:
    SECRET_KEY = "my_secret_key"
    # Set this to True when schools should be allowed to promote learners.
    PROMOTION_ENABLED = False


class DevelopmentConfig(Config):
    DEBUG = True
    # Absolute path to database at top level
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL"
    ) or "sqlite:///" + os.path.join(basedir, "..", "app.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
