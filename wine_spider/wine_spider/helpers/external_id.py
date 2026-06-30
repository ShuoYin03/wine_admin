def build_lot_external_id(auction_id, source_lot_id):
    if auction_id is None:
        raise ValueError("auction_id is required to build a lot external_id")
    if source_lot_id is None:
        raise ValueError("source_lot_id is required to build a lot external_id")

    return f"{auction_id}_{source_lot_id}"
