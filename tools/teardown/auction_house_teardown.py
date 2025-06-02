from database import (
    AuctionsClient,
    LotsClient,
    LotItemsClient,
    AuctionSalesClient,
    LwinMatchingClient,
)

def teardown_by_auction_house(auction_house: str, db_client_map: dict): 
    auction_client = db_client_map["auction"]
    lot_client = db_client_map["lot"]
    lot_item_client = db_client_map["lot_item"]
    lwin_matching_client = db_client_map["lwin_matching"]
    auction_sale_client = db_client_map["auction_sale"]

    with auction_client.session_scope() as session:
        auctions = session.query(auction_client.model).filter_by(auction_house=auction_house).all()
        external_ids = [a.external_id for a in auctions]
        if not external_ids:
            print(f"❌ No auctions found for auction_house: {auction_house}")
            return

        print(f"🧨 Found {len(external_ids)} auctions under '{auction_house}'")

        lots = session.query(lot_client.model).filter(lot_client.model.auction_id.in_(external_ids)).all()
        lot_ids = [lot.id for lot in lots]
        lot_external_ids = [lot.external_id for lot in lots]
        print(f" - Deleting {len(lot_ids)} lots")

        if lot_external_ids:
            session.query(lwin_matching_client.model).filter(
                lwin_matching_client.model.lot_id.in_(lot_external_ids)
            ).delete(synchronize_session=False)

            session.query(lot_item_client.model).filter(
                lot_item_client.model.lot_id.in_(lot_external_ids)
            ).delete(synchronize_session=False)

            session.query(lot_client.model).filter(
                lot_client.model.external_id.in_(lot_external_ids)
            ).delete(synchronize_session=False)

        session.query(auction_sale_client.model).filter(
            auction_sale_client.model.auction_id.in_(external_ids)
        ).delete(synchronize_session=False)

        session.query(auction_client.model).filter(
            auction_client.model.external_id.in_(external_ids)
        ).delete(synchronize_session=False)

        print(f"✅ All data under auction_house '{auction_house}' deleted.")

auctionClient = AuctionsClient()
lotsClient = LotsClient()
lotItemsClient = LotItemsClient()
lwinMatchingClient = LwinMatchingClient()
auctionSalesClient = AuctionSalesClient()

db_client_map = {
    "auction": auctionClient,
    "lot": lotsClient,
    "lot_item": lotItemsClient,
    "lwin_matching": lwinMatchingClient,
    "auction_sale": auctionSalesClient,
}

teardown_by_auction_house("WineAuctioneer", db_client_map)