from flask import Flask
from .routes.match import match_blueprint
from .routes.query import query_blueprint
from .routes.lwin_query import lwin_query_blueprint

def create_app():
    app = Flask(__name__)
    
    app.config.from_object('app.config.Config')

    app.register_blueprint(match_blueprint)
    app.register_blueprint(query_blueprint)
    app.register_blueprint(lwin_query_blueprint)
    
    return app
