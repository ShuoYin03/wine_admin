from flask import Flask
from .routes.match import match_blueprint
from .routes.lot_query import lot_query_blueprint
from .routes.lwin_query import lwin_query_blueprint
from .routes.fx_rates import fx_rates_blueprint
from flask_cors import CORS

def create_app():
    app = Flask(__name__)
    
    CORS(app, resources={r"/*": {"origins": "*"}})

    app.config.from_object('app.config.Config')

    app.register_blueprint(match_blueprint)
    app.register_blueprint(lot_query_blueprint)
    app.register_blueprint(lwin_query_blueprint)
    app.register_blueprint(fx_rates_blueprint)
    
    return app