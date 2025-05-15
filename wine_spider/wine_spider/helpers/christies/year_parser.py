import re

def extract_years_from_json(lot_json: dict) -> list[str]:
    text1 = lot_json.get("title_primary_txt", "")
    text2 = lot_json.get("description_txt", "")
    pattern = r"\b(?:19|20)\d{2}\b"
    
    matches = re.findall(pattern, text1 + " " + text2)
    years = set()
    
    for match in matches:
        if isinstance(match, tuple):
            year = match[0] + match[1:]
        else:
            year = match
        years.add(year)
    
    return sorted(list(years), key=int)

json = {
        "lot_number": "1",
        "end_date_unformatted": "0001-01-01T00:00:00+00:00",
        "start_date_unformatted": "0001-01-01T00:00:00+00:00",
        "is_age_check_required": True,
        "online_only_dynamic_lot_data": {
            "item_id": 209397,
            "next_bid": 35000.0,
            "current_user_max_bid_amount": 0.0,
            "next_bid_text": "Place next bid: HKD 35,000",
            "next_bid_disabled": False,
            "item_status": "Closed"
        },
        "online_only_static_lot_data": {
            "item_id": 209397,
            "lot_id": 209106,
            "is_live_auction_lot": False,
            "header_price": "Estimate: HKD 30,000 - 45,000",
            "christies_unique_identifier": "22660.1"
        },
        "is_open_for_bidding": False,
        "analytics_id": "22660.1",
        "object_id": "209397",
        "lot_id_txt": "1",
        "event_type": "OnlineSale",
        "start_date": "2024-01-19T01:00:00.000Z",
        "end_date": "2024-01-30T04:00:00.000Z",
        "registration_closing_date": "2024-01-30T04:00:00.000Z",
        "countdown_start_date": "2024-01-19T01:00:00.000Z",
        "url": "/s/pristine-contemporary-cellar-online/chateau-lafite-rothschild-2003-1/209397?ldp_breadcrumb=back",
        "title_primary_txt": "Ch\u00e2teau Lafite-Rothschild 2003",
        "title_secondary_txt": "6 Bottles (75cl) per lot",
        "consigner_information": "",
        "description_txt": "<b>Ch\u00e2teau Lafite-Rothschild </b><b>2003</b><br><i>Pauillac, 1er cru class\u00e9<br>In original <b>1900</b>wooden case, banded prior to inspection</i><br>6 Bottles (75cl) <i>per lot</i><br>",
        "image": {
            "image_src": "https://www.christies.com/img/LotImages/2024/HGK/2024_HGK_22660_0001_000(chateau_lafite-rothschild_2003_2003_6_bottles_per_lot065247).jpg?mode=max",
            "image_mobile_src": "https://www.christies.com/img/LotImages/2024/HGK/2024_HGK_22660_0001_000(chateau_lafite-rothschild_2003_2003_6_bottles_per_lot065247).jpg?mode=max",
            "image_tablet_src": "https://www.christies.com/img/LotImages/2024/HGK/2024_HGK_22660_0001_000(chateau_lafite-rothschild_2003_2003_6_bottles_per_lot065247).jpg?mode=max",
            "image_desktop_src": "https://www.christies.com/img/LotImages/2024/HGK/2024_HGK_22660_0001_000(chateau_lafite-rothschild_2003_2003_6_bottles_per_lot065247).jpg?mode=max",
            "image_alt_text": "Ch\u00e2teau Lafite-Rothschild 2003",
            "image_url": "https://www.christies.com/img/LotImages/2024/HGK/2024_HGK_22660_0001_000(chateau_lafite-rothschild_2003_2003_6_bottles_per_lot065247).jpg?mode=max"
        },
        "estimate_visible": True,
        "estimate_on_request": False,
        "price_on_request": False,
        "estimate_low": "30000.00",
        "estimate_high": "45000.00",
        "estimate_txt": "HKD 30,000 - 45,000",
        "price_realised": "40000.00",
        "price_realised_txt": "HKD 40,000",
        "current_bid": "",
        "current_bid_txt": "",
        "is_saved": False,
        "show_save": True,
        "has_no_bids": False,
        "bid_count_txt": " - 3 bids",
        "extended": False,
        "server_time": "2025-05-13T09:41:00.633Z",
        "total_seconds_remaining": -40542061,
        "sale": {
            "time_zone": "TIMEZONE",
            "date_txt": "DATETEXT",
            "start_date": "2024-01-19T01:00:00.000Z",
            "end_date": "2024-01-30T04:00:00.000Z",
            "is_in_progress": False
        },
        "lot_withdrawn": False,
        "bid_status": {
            "txt": "",
            "status": ""
        },
        "seconds_until_bidding": -41503261,
        "show_timer": True,
        "bid_button_action": {
            "aria_button_txt": "Bid",
            "show": False,
            "is_enabled": False,
            "button_txt": "Bid",
            "action_event_name": "auction-signin",
            "action_display": "online-modal",
            "action_type": "id",
            "action_value": "online-login"
        }
    }
# print(extract_years_from_json(json))