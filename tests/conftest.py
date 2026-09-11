import os

os.environ["FLASK_ENV"] = "testing"

import pytest

from app import create_app
from app.extensions import db as _db


@pytest.fixture()
def app():
    application = create_app()
    application.config.update(TESTING=True)

    with application.app_context():
        yield application


@pytest.fixture()
def db(app):
    yield _db
    _db.session.remove()
