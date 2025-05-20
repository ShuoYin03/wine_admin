from flask import Flask
from .routes.match import match_blueprint
from .routes.lot_query import lot_query_blueprint
from .routes.lwin_query import lwin_query_blueprint
# from .routes.fx_rates import fx_rates_blueprint
from .routes.auction_query import auction_query_blueprint
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from database import (
    LotsClient,
    AuctionsClient,
    LotItemsClient,
    AuctionSalesClient,
    FxRatesClient,
    LwinMatchingClient,
    LwinDatabaseClient,
)
from app.service.lwin_matching_service import LwinMatchingService

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
        app.lwin_matching_service = LwinMatchingService(lwin_database_client.get_all())

    app.register_blueprint(match_blueprint)
    app.register_blueprint(lot_query_blueprint)
    app.register_blueprint(lwin_query_blueprint)
    # app.register_blueprint(fx_rates_blueprint)
    app.register_blueprint(auction_query_blueprint)
    
    return app