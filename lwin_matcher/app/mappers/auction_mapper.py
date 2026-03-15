from __future__ import annotations
from app.models.auction import Auction
from app.models.auction_sales import AuctionSales
from app.models.lot import Lot
from shared.database.models.auction_db import AuctionModel


def map_auction(orm_auction: AuctionModel, include_lots: bool = False) -> Auction:
    return Auction(
        **{
            field: getattr(orm_auction, field)
            for field in Auction.model_fields
            if field not in ("sales", "lots") and hasattr(orm_auction, field)
        },
        sales=AuctionSales.model_validate(orm_auction.auction_sales) if orm_auction.auction_sales else None,
        lots=[Lot.model_validate(lot) for lot in orm_auction.lots] if include_lots else None,
    )
