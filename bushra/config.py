import os

basedir = os.path.abspath(os.path.dirname(__file__))  # points to bushra/


class Config:
    SECRET_KEY = "my_secret_key"


class DevelopmentConfig(Config):
    DEBUG = True
    # Absolute path to database at top level
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL"
    ) or "sqlite:///" + os.path.join(basedir, "..", "app.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
