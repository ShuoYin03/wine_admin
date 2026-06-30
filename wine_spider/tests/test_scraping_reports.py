import json
import importlib.util
import sys
from pathlib import Path

from wine_spider.services.bonhams_client import BonhamsClient
from wine_spider.helpers import (
    build_zachys_categories_url,
    extract_zachys_lot_count_from_categories,
    extract_zachys_past_catalog_links,
)
from wine_spider.spiders.reports import generate_bonhams_report
from wine_spider.spiders.reports import generate_sothebys_report
from wine_spider.spiders.reports import generate_steinfels_report
from wine_spider.spiders.reports import generate_wineauctioneer_report
from wine_spider.spiders.reports import generate_zachys_report
from wine_spider.spiders.reports.generate_zachys_report import ZachysReportSpider


RUNNER_PATH = Path(__file__).resolve().parents[1] / "scripts" / "run_scraping_reports.py"
spec = importlib.util.spec_from_file_location("run_scraping_reports", RUNNER_PATH)
run_scraping_reports = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = run_scraping_reports
spec.loader.exec_module(run_scraping_reports)


def test_bonhams_report_uses_current_service_endpoint_and_headers():
    client = BonhamsClient()

    api_url, headers = generate_bonhams_report.get_bonhams_report_api_config()

    assert api_url == client.api_url
    assert headers["x-typesense-api-key"] == client.headers["x-typesense-api-key"]


def test_sothebys_report_reads_algolia_key_from_graphql_response():
    payload = {"data": {"algoliaSearchKey": {"key": "real-key"}}}

    assert generate_sothebys_report.extract_algolia_key(payload) == "real-key"


def test_steinfels_report_uses_lot_api_total_count_over_catalog_lot_number_end():
    lot_response = {"$totalCount": 126, "items": [{}] * 100}
    auction = {"catalogs": [{"parts": [{"lotNumberEnd": 127}]}]}

    assert generate_steinfels_report.extract_expected_lot_count(lot_response, auction) == 126


def test_wineauctioneer_report_builds_cookie_mapping_from_storage_state():
    storage_state = {
        "cookies": [
            {"name": "session", "value": "abc"},
            {"name": "tracking", "value": "def"},
        ]
    }

    assert generate_wineauctioneer_report.cookies_from_storage_state(storage_state) == {
        "session": "abc",
        "tracking": "def",
    }


def test_wineauctioneer_report_loads_cookie_mapping_from_file():
    state_path = Path("exports/test_wineauctioneer_cookies.json")
    state_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        state_path.write_text(
            json.dumps({"cookies": [{"name": "session", "value": "abc"}]}),
            encoding="utf-8",
        )

        assert generate_wineauctioneer_report.load_cookies(state_path) == {"session": "abc"}
    finally:
        state_path.unlink(missing_ok=True)


def test_wineauctioneer_report_extracts_encoded_pagination_urls():
    html = """
    <a href="?page=0%2C1%2C0%2C0%2C0">2</a>
    <a href="?page=0%2C2%2C0%2C0%2C0">3</a>
    """

    assert generate_wineauctioneer_report.extract_pagination_urls(html) == [
        "https://wineauctioneer.com/wine-auctions?page=0%2C1%2C0%2C0%2C0",
        "https://wineauctioneer.com/wine-auctions?page=0%2C2%2C0%2C0%2C0",
    ]


def test_wineauctioneer_report_fetches_lots_with_listing_referer(monkeypatch):
    calls = []

    class Response:
        status_code = 200
        text = "<html></html>"

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return Response()

    monkeypatch.setattr(generate_wineauctioneer_report.cffi_requests, "get", fake_get)

    html = generate_wineauctioneer_report.fetch_html(
        "https://wineauctioneer.com/wine-auctions/january-2026-auction/lots",
        cookies={"Wa_Role": "0"},
        referer="https://wineauctioneer.com/wine-auctions",
    )

    assert html == "<html></html>"
    assert calls[0][1]["headers"]["referer"] == "https://wineauctioneer.com/wine-auctions"
    assert calls[0][1]["headers"]["sec-fetch-site"] == "same-origin"
    assert calls[0][1]["headers"]["sec-fetch-mode"] == "navigate"


def test_zachys_report_enables_waf_for_report_spider():
    enabled_spiders = ZachysReportSpider.custom_settings["AWS_WAF_ENABLED_SPIDERS"]

    assert "zachys_report_spider" in enabled_spiders


def test_zachys_report_uses_category_endpoint_lot_count():
    assert build_zachys_categories_url(161) == (
        "https://bid.zachys.com/search/get-categories"
        "?auction_id=161&page_type=catalog-list&is_more=0"
    )
    payload = {
        "success": True,
        "payload": {
            "categories": [
                {"name": "Type", "lots_qty": 1565},
                {"name": "Country", "lots_qty": 1565},
            ]
        },
    }

    assert extract_zachys_lot_count_from_categories(payload) == 1565


def test_zachys_landing_parser_reads_full_latest_results_block():
    html = """
    <div class="row">
      <div>
        <div class="block">
          <div class="past-auctions">
            <h1>Latest Auction Results</h1>
            <div class="upcoming-auction-item">
              <a href="https://bid.zachys.com/auctions/catalog/id/161/Fine-Rare-Wines-Delaware-June-18-19"></a>
              <div class="upcoming-auction-text">
                <a href="https://bid.zachys.com/auctions/catalog/id/161/Fine-Rare-Wines-Delaware-June-18-19">
                  Fine & Rare Wines, Delaware, June 25 & 26
                </a>
              </div>
            </div>
          </div>
        </div>
        <div class="upcoming-auction-item">
          <a href="https://bid.zachys.com/auctions/catalog/id/163/zCollections-New-York-June-2-15"></a>
          <div class="upcoming-auction-text">
            <a href="https://bid.zachys.com/auctions/catalog/id/163/zCollections-New-York-June-2-15">
              zCollections, New York, June 9 - 22
            </a>
          </div>
        </div>
      </div>
    </div>
    """

    links = extract_zachys_past_catalog_links(html, current_year=2026)

    assert [link.auction_id for link in links] == ["161", "163"]
    assert links[1].start_date == "2026-06-09"
    assert links[1].end_date == "2026-06-22"


def test_zachys_extracts_auction_rows_from_listing_html():
    html = """
    <script data-server="true">
    {"default":{"auctionRows":[{"id":"161","name":"Fine Sale","auction_seo_url":"Fine-Sale","total_lots":"1565"}]}}
    </script>
    """

    rows = generate_zachys_report.extract_zachys_auction_rows(html)

    assert rows == [
        {
            "id": "161",
            "name": "Fine Sale",
            "auction_seo_url": "Fine-Sale",
            "total_lots": "1565",
        }
    ]


def test_zachys_direct_report_uses_past_listing_auction_rows(monkeypatch):
    monkeypatch.setattr(
        generate_zachys_report,
        "fetch_zachys_past_auction_rows",
        lambda: [
            {
                "id": "161",
                "name": "Fine & Rare Wines, Delaware, June 25 & 26",
                "auction_seo_url": "Fine-Rare-Wines-Delaware-June-18-19",
                "total_lots": "1565",
            }
        ],
    )

    class FakeReport:
        instances = []

        def __init__(self, auction_house):
            self.auction_house = auction_house
            self.rows = []
            self.exported = False
            FakeReport.instances.append(self)

        def load_lot_counts_from_db(self):
            return [
                {
                    "external_id": "zachys_161",
                    "url": "https://bid.zachys.com/auctions/catalog/id/161/Fine-Rare-Wines-Delaware-June-18-19",
                    "lot_count": 1565,
                }
            ]

        def add_result(self, **kwargs):
            self.rows.append(kwargs)

        def export(self):
            self.exported = True

    monkeypatch.setattr(generate_zachys_report, "AuctionScrapingReportGenerator", FakeReport)

    generate_zachys_report.run_report()

    report = FakeReport.instances[0]
    assert report.exported is True
    assert report.rows == [
        {
            "external_id": "zachys_161",
            "hits": 1565,
            "lot_count": 1565,
            "match": True,
            "url": "https://bid.zachys.com/auctions/catalog/id/161/Fine-Rare-Wines-Delaware-June-18-19",
        }
    ]


def test_scraping_report_runner_parses_comma_separated_houses():
    assert run_scraping_reports.parse_house_values(["wineauctioneer,sothebys", "tajan"]) == [
        "wineauctioneer",
        "sothebys",
        "tajan",
    ]


def test_scraping_report_runner_reads_houses_from_npm_env():
    assert run_scraping_reports.resolve_house_values([], {"npm_config_houses": "wineauctioneer"}) == [
        "wineauctioneer"
    ]


def test_scraping_report_runner_resolves_single_house_module():
    reports, include_zachys = run_scraping_reports.resolve_report_selection(["wineauctioneer"])

    assert reports == [
        ("Wineauctioneer", "wine_spider.spiders.reports.generate_wineauctioneer_report", 240)
    ]
    assert include_zachys is False


def test_scraping_report_runner_all_includes_zachys():
    reports, include_zachys = run_scraping_reports.resolve_report_selection(["all"])

    assert ("Wineauctioneer", "wine_spider.spiders.reports.generate_wineauctioneer_report", 240) in reports
    assert include_zachys is True
