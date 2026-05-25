from flask_sqlalchemy import SQLAlchemy
import os

db = SQLAlchemy()

def init_db(app):

    BASE_DIR = os.path.abspath(
        os.path.dirname(__file__)
    )

    db_path = os.path.join(
        BASE_DIR,
        "instance",
        "annotation.db"
    )

    app.config[
        "SQLALCHEMY_DATABASE_URI"
    ] = "///" + db_path

    app.config[
        "SQLALCHEMY_TRACK_MODIFICATIONS"
    ] = False

    db.init_app(app)