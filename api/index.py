from app import app as flask_app


app = flask_app


def handler(environ, start_response):
    return flask_app.wsgi_app(environ, start_response)
