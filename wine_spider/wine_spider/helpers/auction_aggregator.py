def compute_auction_sales_stats(lots, lot_items):
    """
    Compute aggregated sales statistics for a single auction.

    Args:
        lots: Iterable of lot dicts with keys: original_currency, low_estimate,
              high_estimate, sold, end_price, volume, external_id.
        lot_items: Iterable of lot-detail dicts with key: lot_producer.

    Returns:
        dict with keys: lots, sold, currency, total_low_estimate,
        total_high_estimate, total_sales, volume_sold, top_lot,
        top_lot_price, single_cellar.
    """
    stats = {
        "lots": 0,
        "sold": 0,
        "total_low_estimate": 0,
        "total_high_estimate": 0,
        "total_sales": 0,
        "volume_sold": 0,
        "top_lot": None,
        "top_lot_price": 0,
        "single_cellar_check": None,
        "single_cellar": True,
        "currency": None,
    }

    for lot in lots:
        if lot.get("original_currency") and stats["currency"] is None:
            stats["currency"] = lot["original_currency"]
        stats["lots"] += 1
        stats["total_low_estimate"] += int(lot.get("low_estimate") or 0)
        stats["total_high_estimate"] += int(lot.get("high_estimate") or 0)
        if lot.get("sold"):
            price = int(lot.get("end_price") or 0)
            stats["sold"] += 1
            stats["total_sales"] += price
            stats["volume_sold"] += float(lot.get("volume") or 0)
            if price > stats["top_lot_price"]:
                stats["top_lot_price"] = price
                stats["top_lot"] = lot.get("external_id")

    for lot_item in lot_items:
        producer = lot_item.get("lot_producer")
        if producer is None:
            continue
        if stats["single_cellar_check"] is None:
            stats["single_cellar_check"] = producer
        elif stats["single_cellar_check"] != producer:
            stats["single_cellar"] = False

    return stats
