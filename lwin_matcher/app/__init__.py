from flask import Flask
from app.routes.match import match_blueprint
from app.routes.lot_query import lot_query_blueprint
from app.routes.lwin_query import lwin_query_blueprint
# from app.routes.fx_rates import fx_rates_blueprint
from app.routes.auction_query import auction_query_blueprint
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

from shared.database.lots_client import LotsClient
from shared.database.auctions_client import AuctionsClient
from shared.database.lot_items_client import LotItemsClient
from shared.database.auction_sales_client import AuctionSalesClient
from shared.database.fx_rates_client import FxRatesClient
from shared.database.lwin_matching_client import LwinMatchingClient
from shared.database.lwin_database_client import LwinDatabaseClient

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    
    CORS(app, resources={r"/*": {"origins": "*"}})
    app.config.from_object('app.config.Config')

    db.init_app(app)
    app.lots_client = LotsClient(db_instance=db)
    app.auctions_client = AuctionsClient(db_instance=db)
    app.lot_items_client = LotItemsClient(db_instance=db)
    app.auction_sales_client = AuctionSalesClient(db_instance=db)
    app.fx_rates_client = FxRatesClient(db_instance=db)
    app.lwin_matching_client = LwinMatchingClient(db_instance=db)
    lwin_database_client = LwinDatabaseClient(db_instance=db)
    app.lwin_database_client = lwin_database_client
    with app.app_context():
        from app.service.lwin_matching_engine import LwinMatcherEngine
        app.lwin_matching_engine = LwinMatcherEngine(lwin_database_client.get_all())

    app.register_blueprint(match_blueprint)
    app.register_blueprint(lot_query_blueprint)
    app.register_blueprint(lwin_query_blueprint)
    app.register_blueprint(auction_query_blueprint)
    
    return app