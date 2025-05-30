def teardown_by_auction_house(auction_house: str, db_client_map: dict): 
    auction_client = db_client_map["auction"]
    lot_client = db_client_map["lot"]
    lot_item_client = db_client_map["lot_item"]
    lwin_matching_client = db_client_map["lwin_matching"]
    auction_sale_client = db_client_map["auction_sale"]

    with auction_client.session_scope() as session:
        auctions = session.query(auction_client.model).filter_by(auction_house=auction_house).all()
        auction_ids = [a.id for a in auctions]
        if not auction_ids:
            print(f"❌ No auctions found for auction_house: {auction_house}")
            return

        print(f"🧨 Found {len(auction_ids)} auctions under '{auction_house}'")

        lots = session.query(lot_client.model).filter(lot_client.model.auction_id.in_(auction_ids)).all()
        lot_ids = [lot.id for lot in lots]
        print(f" - Deleting {len(lot_ids)} lots")

        if lot_ids:
            session.query(lwin_matching_client.model).filter(lwin_matching_client.model.lot_id.in_(lot_ids)).delete(synchronize_session=False)
            session.query(lot_item_client.model).filter(lot_item_client.model.lot_id.in_(lot_ids)).delete(synchronize_session=False)
            session.query(auction_sale_client.model).filter(auction_sale_client.model.lot_id.in_(lot_ids)).delete(synchronize_session=False)
            session.query(lot_client.model).filter(lot_client.model.id.in_(lot_ids)).delete(synchronize_session=False)

        session.query(auction_client.model).filter(auction_client.model.id.in_(auction_ids)).delete(synchronize_session=False)

        print(f"✅ All data under auction_house '{auction_house}' deleted.")

db_client_map = {
    "auction": AuctionClient,
    "lot": LotClient,
    "lot_item": LotItemClient,
    "lwin_matching": LwinMatchingClient,
    "auction_sale": AuctionSaleClient,
}

teardown_by_auction_house("WineAuctioneer", db_client_map)