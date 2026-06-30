from wine_spider.services.bonhams_client import BonhamsClient
from wine_spider.helpers.bonhams.lot_parser import BonhamsLotParser


def test_client_parses_auction_api_response_without_regex_name_error():
    client = BonhamsClient()
    response = {
        "results": [
            {
                "hits": [
                    {
                        "document": {
                            "id": "32584",
                            "auctionTitle": "Pacific Provenance: Refined Wines",
                            "dates": {
                                "start": {
                                    "timezone": {"iana": "Europe/London"},
                                    "datetime": "2026-06-01T10:00:00+00:00",
                                },
                                "end": {"datetime": "2026-06-02T10:00:00+00:00"},
                            },
                            "year": "2026",
                            "month": "June",
                            "auctionType": "ONLINE",
                        }
                    }
                ]
            }
        ]
    }

    auctions = client.parse_auction_api_response(response)

    assert len(auctions) == 1
    assert auctions[0]["external_id"] == "32584"
    assert auctions[0]["auction_house"] == "Bonhams"
    assert auctions[0]["city"] == "London"


def test_parser_uses_catalog_desc_bold_entries_as_lot_components():
    parser = BonhamsLotParser()
    catalog_desc = """
    <div class="LotHeading">Port</div><div class="LotName"></div>
    <div class="LotDesc">
      <B>Cockburn's, 1950 (1 x 750ml)</B><I><br />Region: Portugal</I><br />
      <B>Taylor's, Vargellas Vinha Velha, 2011 (3 x 750ml)</B><I><br />Region: Portugal</I>
    </div>
    """

    components = parser.parse_components(
        "Cockburn's, 1950 (1 x 750ml) Taylor's, Vargellas Vinha Velha, 2011 (3 x 750ml)",
        catalog_desc,
    )

    assert [component.title for component in components] == [
        "Cockburn's, 1950 (1 x 750ml)",
        "Taylor's, Vargellas Vinha Velha, 2011 (3 x 750ml)",
    ]
    assert [component.producer for component in components] == ["Cockburn's", "Taylor's"]
    assert [component.vintage for component in components] == ["1950", "2011"]
    assert [component.unit_format for component in components] == ["750 ml", "750 ml"]
    assert [component.region for component in components] == ["Portugal", "Portugal"]


def test_parser_does_not_use_lwin_fuzzy_guess_for_producer():
    parser = BonhamsLotParser()
    catalog_desc = """
    <div class="LotDesc">
      <B>Produttori del Barbaresco, Riserva Cru Assortment, 2020 (9 x 750ml)</B><I><br />Region: Piedmont</I><br />
      <B>Canalicchio di Sopra, Brunello di Montalcino, 2019 (6 x 750ml)</B><I><br />Region: Tuscany</I>
    </div>
    """

    components = parser.parse_components(
        "Produttori del Barbaresco, Riserva Cru Assortment, 2020 (9 x 750ml) "
        "Canalicchio di Sopra, Brunello di Montalcino, 2019 (6 x 750ml)",
        catalog_desc,
    )

    assert [component.producer for component in components] == [
        "Produttori del Barbaresco",
        "Canalicchio di Sopra",
    ]


def test_parser_falls_back_to_title_bracket_split_when_catalog_desc_is_missing():
    parser = BonhamsLotParser()

    components = parser.parse_components(
        "Dom Pérignon, 1999 (12 x 750ml) Opus One, 2015 (6 x 750ml)",
        None,
    )

    assert [component.title for component in components] == [
        "Dom Pérignon, 1999 (12 x 750ml)",
        "Opus One, 2015 (6 x 750ml)",
    ]
    assert [component.producer for component in components] == ["Dom Pérignon", "Opus One"]


def test_client_maps_catalog_components_to_lot_detail_items():
    client = BonhamsClient()
    response = {
        "results": [
            {
                "hits": [
                    {
                        "document": {
                            "id": "32214-362",
                            "auctionId": "32214",
                            "title": (
                                "Produttori del Barbaresco, Riserva Cru Assortment, 2020 (9 x 750ml) "
                                "Canalicchio di Sopra, Brunello di Montalcino, 2019 (6 x 750ml)"
                            ),
                            "catalogDesc": (
                                "<div class='LotDesc'>"
                                "<B>Produttori del Barbaresco, Riserva Cru Assortment, 2020 (9 x 750ml)</B>"
                                "<I><br />Region: Piedmont</I><br />"
                                "<B>Canalicchio di Sopra, Brunello di Montalcino, 2019 (6 x 750ml)</B>"
                                "<I><br />Region: Tuscany</I>"
                                "</div>"
                            ),
                            "department": {"name": "Wine"},
                            "currency": {"iso_code": "GBP"},
                            "price": {"hammerPrice": 0, "estimateLow": 100, "estimateHigh": 200},
                            "status": "UNSOLD",
                            "hammerTime": {"datetime": "2026-01-01T00:00:00+00:00"},
                            "region": {"name": "United Kingdom"},
                            "country": {"name": "United Kingdom"},
                        }
                    }
                ]
            }
        ]
    }

    [(lot_item, lot_detail_items)] = client.parse_lot_api_response(response)

    assert lot_item["region"] == "Piedmont"
    assert lot_item["country"] == "Italy"
    assert [item["lot_producer"] for item in lot_detail_items] == [
        "Produttori del Barbaresco",
        "Canalicchio di Sopra",
    ]
    assert [item["vintage"] for item in lot_detail_items] == [2020, 2019]
    assert [item["unit_format"] for item in lot_detail_items] == ["750 ml", "750 ml"]


def test_lot_search_payload_keeps_catalog_desc_for_component_parsing():
    client = BonhamsClient()

    payload = client.get_lot_search_payload("32214")
    excluded_fields = payload["searches"][0].get("exclude_fields", "")

    assert "catalogDesc" not in excluded_fields
    assert "footnotes" in excluded_fields
