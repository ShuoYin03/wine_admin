import asyncio
import logging
from types import SimpleNamespace
from unittest.mock import Mock

from wine_spider.helpers.tajan.lot_detail_parser import TajanLotDetailParser
from wine_spider.helpers.tajan.progress import TajanProgressTracker
from wine_spider.items import LotItem
from wine_spider.spiders import tajan as tajan_spider_module
from wine_spider.spiders.tajan import (
    TajanSpider,
    build_tajan_proxy_contexts,
    parse_tajan_proxy_entry,
)

from scrapy import Request
from scrapy.http import HtmlResponse


async def collect_async(async_iterable):
    return [item async for item in async_iterable]


def test_extracts_producer_from_first_segment_when_it_is_producer():
    parser = TajanLotDetailParser()

    result = parser.parse_detail_text("6 bouteilles PETRUS, Pomerol 2007 CB | Cave 1 |")

    assert result.description == "6 bouteilles PETRUS, Pomerol 2007 CB"
    assert result.producer_candidates == ("Petrus",)
    assert result.vintages == ("2007",)
    assert result.match_text == "Petrus Pomerol 2007"


def test_extracts_producer_from_later_domain_segment():
    parser = TajanLotDetailParser()

    result = parser.parse_detail_text(
        "3 bouteilles BATARD-MONTRACHET, Domaine Leflaive 2011 | Cave 2 |"
    )

    assert result.producer_candidates == ("Domaine Leflaive",)
    assert result.vintages == ("2011",)
    assert result.match_text == "Domaine Leflaive BATARD-MONTRACHET 2011"


def test_extracts_chateau_producer_from_first_segment():
    parser = TajanLotDetailParser()

    result = parser.parse_detail_text(
        "1 bouteille Chateau D'YQUEM, 1° cru supérieur Sauternes 1990"
    )

    assert result.producer_candidates == ("Chateau D'Yquem",)
    assert result.vintages == ("1990",)
    assert result.match_text == "Chateau D'Yquem 1° cru supérieur Sauternes 1990"


def test_extracts_producer_from_third_segment():
    parser = TajanLotDetailParser()

    result = parser.parse_detail_text(
        "12 bouteilles CHAMBOLLE-MUSIGNY, 1° cru Les Sentiers, Domaine Duband 2011"
    )

    assert result.producer_candidates == ("Domaine Duband",)
    assert result.vintages == ("2011",)
    assert result.match_text == "Domaine Duband CHAMBOLLE-MUSIGNY 1° cru Les Sentiers 2011"

def test_strips_payment_footer_before_extracting_producer():
    parser = TajanLotDetailParser()

    result = parser.parse_detail_text(
        "12 Btlles Chambolle Musigny Domaine Remy Jeanniard 2004 "
        "Payment & Shipping Accepted Forms Of Payment: American Express"
    )

    assert result.description == "12 Btlles Chambolle Musigny Domaine Remy Jeanniard 2004"
    assert result.producer_candidates == ("Domaine Remy Jeanniard",)
    assert result.vintages == ("2004",)
    assert result.match_text == "Domaine Remy Jeanniard Chambolle Musigny 2004"


def test_does_not_guess_mixed_ensemble_description_as_producer():
    parser = TajanLotDetailParser()

    result = parser.parse_detail_text(
        "Ensemble de 12 bouteilles 6 bouteilles Saint-Estephe Bourie Manoux "
        "1 bouteille Chateau Grand Mirande 1 bouteille Chateau Grand Puch 1978"
    )

    assert result.producer_candidates == ()
    assert result.vintages == ("1978",)


def test_does_not_guess_when_only_appellation_segments_are_present():
    parser = TajanLotDetailParser()

    result = parser.parse_detail_text("3 magnums CHAMBERTIN, Clos de Beze, Bart 2009")

    assert result.producer_candidates == ()
    assert result.vintages == ("2009",)
    assert result.match_text == "CHAMBERTIN Clos de Beze Bart 2009"


def test_spider_uses_detail_description_for_lot_detail_items(monkeypatch):
    spider = TajanSpider.__new__(TajanSpider)
    spider.lot_detail_parser = TajanLotDetailParser()
    spider.lwin_df = object()

    def fake_match_lot_info(title, df, throw_exception=True, **kwargs):
        assert title == "Domaine Leflaive BATARD-MONTRACHET 2011"
        assert throw_exception is False
        return None, "Burgundy", "Cote de Beaune", "France"

    monkeypatch.setattr(tajan_spider_module, "match_lot_info", fake_match_lot_info)

    lot_item = LotItem()
    lot_item["external_id"] = "tajan_test-auction_3"
    lot_item["lot_name"] = "3 bouteilles BATARD-MONTRACHET"
    response = HtmlResponse(
        url="https://www.tajan.com/en/auction-lot/3-bouteilles-batard-montrachet",
        request=Request(
            url="https://www.tajan.com/en/auction-lot/3-bouteilles-batard-montrachet",
            meta={"lot_item": lot_item},
        ),
        body=(
            b"<div class='lot-info border-bottom'>"
            b"3 bouteilles BATARD-MONTRACHET, Domaine Leflaive 2011 | Cave 2 |"
            b"</div>"
        ),
        encoding="utf-8",
    )

    results = list(spider.parse_lot_detail(response))

    assert results[0]["lot_name"] == "3 bouteilles BATARD-MONTRACHET, Domaine Leflaive 2011"
    assert results[0]["region"] == "Burgundy"
    assert results[0]["sub_region"] == "Cote de Beaune"
    assert results[0]["country"] == "France"
    assert results[0]["unit"] == 3
    assert results[0]["volume"] == 2250
    assert results[1]["lot_id"] == "tajan_test-auction_3"
    assert results[1]["lot_producer"] == "Domaine Leflaive"
    assert results[1]["vintage"] == "2011"
    assert results[1]["unit_format"] == "bottle"


def test_spider_parses_listing_volume_and_detail_unit_format():
    spider = TajanSpider.__new__(TajanSpider)
    response = HtmlResponse(
        url="https://www.tajan.com/auction-catalog/wine-and-spirit?pageNum=1",
        body=b"""
        <div>
          <h2 class="lot-title-block">
            <a href="/auction-lot/12-bouteilles-chateau-broustet">
              12: 12 bouteilles Chateau BROUSTET, Barsac 1998 cb
            </a>
          </h2>
          <p class="lot-estimate">Estimate: EUR 170 - 190</p>
        </div>
        """,
        encoding="utf-8",
    )

    selector = response.css("div")[0]
    lot_item = spider.build_lot_item_from_listing(selector, "tajan_test-auction", response)
    results = list(
        spider.yield_lot_with_detail_items(
            lot_item,
            ["Chateau Broustet"],
            ["1998"],
        )
    )

    assert lot_item["unit"] == 12
    assert lot_item["volume"] == 9000
    assert results[1]["unit_format"] == "bottle"


def test_spider_parses_magnum_and_demi_litre_tajan_volume():
    spider = TajanSpider.__new__(TajanSpider)

    assert spider.extract_volume_from_lot_name("1 magnum CHAMPAGNE Bollinger 1999") == (
        1,
        "magnum",
        1500,
    )
    assert spider.extract_volume_from_lot_name("12demi-litres Chateau GUIRAUD 1997") == (
        12,
        "500ml",
        6000,
    )


def test_spider_parses_jeroboam_and_double_magnum_tajan_volume():
    spider = TajanSpider.__new__(TajanSpider)

    assert spider.extract_volume_from_lot_name(
        "1 jéroboam Crozes-Hermitage Cuvée L Domaine Combier Rouge 2023"
    ) == (
        1,
        "jeroboam",
        3000,
    )
    assert spider.extract_volume_from_lot_name(
        "1 double-magnum Château Léoville Las Cases 2020"
    ) == (
        1,
        "double-magnum",
        3000,
    )


def test_spider_normalizes_lot_urls_to_english_detail_route():
    spider = TajanSpider.__new__(TajanSpider)
    response = HtmlResponse(url="https://www.tajan.com/en/auction/wine-sale/")

    result = spider.normalize_lot_url(response, "/auction-lot/6-bouteilles-petrus")

    assert result == "https://www.tajan.com/en/auction-lot/6-bouteilles-petrus"


def test_spider_uses_listing_when_matched_producer_is_in_title(monkeypatch):
    spider = TajanSpider.__new__(TajanSpider)
    spider.lwin_df = object()

    def fake_match_lot_info(title, df, throw_exception=True, **kwargs):
        assert title == "6 bouteilles PETRUS 2007"
        return "Petrus", "Bordeaux", "Pomerol", "France"

    monkeypatch.setattr(tajan_spider_module, "match_lot_info", fake_match_lot_info)

    lot_item = LotItem()
    lot_item["lot_name"] = "6 bouteilles PETRUS 2007"

    result = spider.parse_lot_from_listing_when_confident(lot_item)

    assert result == (["Petrus"], [2007])
    assert lot_item["region"] == "Bordeaux"
    assert lot_item["sub_region"] == "Pomerol"
    assert lot_item["country"] == "France"


def test_spider_keeps_detail_request_when_matched_producer_is_not_in_title(monkeypatch):
    spider = TajanSpider.__new__(TajanSpider)
    spider.lwin_df = object()

    def fake_match_lot_info(title, df, throw_exception=True, **kwargs):
        assert title == "3 bouteilles BATARD-MONTRACHET"
        return "Domaine Leflaive", "Burgundy", "Cote de Beaune", "France"

    monkeypatch.setattr(tajan_spider_module, "match_lot_info", fake_match_lot_info)

    lot_item = LotItem()
    lot_item["lot_name"] = "3 bouteilles BATARD-MONTRACHET"

    result = spider.parse_lot_from_listing_when_confident(lot_item)

    assert result is None
    assert "region" not in lot_item


def test_spider_keeps_detail_request_when_listing_has_no_vintage():
    spider = TajanSpider.__new__(TajanSpider)
    spider.lwin_df = object()

    lot_item = LotItem()
    lot_item["lot_name"] = "6 bouteilles PETRUS"

    result = spider.parse_lot_from_listing_when_confident(lot_item)

    assert result is None


def test_spider_detail_requests_wait_for_domcontentloaded(caplog):
    spider = TajanSpider.__new__(TajanSpider)
    spider.progress_tracker = TajanProgressTracker()
    spider.progress_tracker.record_discovered_auction(
        "tajan_test-auction",
        "Test Auction",
        "https://www.tajan.com/en/auction/test",
    )
    spider.progress_tracker.complete_discovery()
    spider.progress_tracker.mark_started("tajan_test-auction")
    spider.parse_lot_from_listing_when_confident = Mock(return_value=None)
    html = """
    <div class="row lot-container">
      <div>
        <h2 class="lot-title-block">
          <a href="/auction-lot/6-bouteilles-petrus_F3C2380232">275: 6 bouteilles PETRUS</a>
        </h2>
        <p class="lot-estimate">Estimate: €100 - €200</p>
      </div>
    </div>
    """
    request = Request(
        url="https://www.tajan.com/v1/auction-catalog/wine-and-spirit?pageNum=1",
        meta={"auction_id": "tajan_test-auction"},
    )
    response = HtmlResponse(
        url=request.url,
        request=request,
        body=html.encode("utf-8"),
        encoding="utf-8",
    )

    caplog.set_level(logging.INFO)
    [detail_request] = list(spider.parse_auction_page(response))

    assert detail_request.meta["allow_offsite"] is True
    assert detail_request.meta["curl_cffi"] is True
    assert detail_request.meta["curl_cffi_referer"] == response.url
    assert detail_request.meta["dont_retry"] is True
    assert "playwright" not in detail_request.meta
    auction_progress = spider.progress_tracker.auction("tajan_test-auction")
    assert auction_progress.lots_seen == 1
    assert auction_progress.detail_requests == 1
    assert auction_progress.pending_detail == 1
    assert any("Tajan catalog progress:" in message for message in caplog.messages)


def test_spider_discovers_all_tajan_auctions_before_scheduling_requests(caplog):
    spider = TajanSpider.__new__(TajanSpider)
    spider.auction_client = Mock()
    spider.should_skip_existing_auction = Mock(return_value=False)
    page_1 = HtmlResponse(
        url="https://www.tajan.com/en/past/",
        request=Request(url="https://www.tajan.com/en/past/"),
        body=b"""
        <div id="plab__results-container">
          <div class="widget-event">
            <h2 class="event__title"><a href="https://www.tajan.com/en/auction/wine-one/">Wine One</a></h2>
            <div class="event__date">Monday, January 1, 2024</div>
            <div class="event__time mb-0">10:00</div>
            <div class="event__location mb-0">Paris, France</div>
          </div>
        </div>
        <a class="next pagination" href="https://www.tajan.com/en/past/page/2">Next</a>
        """,
        encoding="utf-8",
    )
    page_2 = HtmlResponse(
        url="https://www.tajan.com/en/past/page/2",
        request=Request(url="https://www.tajan.com/en/past/page/2"),
        body=b"""
        <div id="plab__results-container">
          <div class="widget-event">
            <h2 class="event__title"><a href="https://www.tajan.com/en/auction/spirits-two/">Spirits Two</a></h2>
            <div class="event__date">Tuesday, January 2, 2024</div>
            <div class="event__time mb-0">11:00</div>
            <div class="event__location mb-0">Paris, France</div>
          </div>
        </div>
        """,
        encoding="utf-8",
    )

    caplog.set_level(logging.INFO)
    first_results = asyncio.run(collect_async(spider.parse(page_1)))
    assert len(first_results) == 1
    assert isinstance(first_results[0], Request)
    assert spider.progress_tracker.total_auctions == 1
    assert spider.progress_tracker.discovery_complete is False
    spider.should_skip_existing_auction.assert_not_called()

    final_results = asyncio.run(collect_async(spider.parse(page_2)))
    auction_items = [item for item in final_results if not isinstance(item, Request)]
    auction_requests = [item for item in final_results if isinstance(item, Request)]

    assert len(auction_items) == 2
    assert len(auction_requests) == 2
    assert auction_items[0]["start_date"] == "2024-01-01"
    assert auction_items[0]["end_date"] == "2024-01-01"
    assert auction_items[1]["start_date"] == "2024-01-02"
    assert auction_items[1]["end_date"] == "2024-01-02"
    assert all(request.meta["allow_offsite"] is True for request in auction_requests)
    assert spider.progress_tracker.total_auctions == 2
    assert spider.progress_tracker.discovery_complete is True
    assert spider.should_skip_existing_auction.call_count == 2
    assert any(
        "Tajan discovery:" in message and "discovery_complete=True" in message
        for message in caplog.messages
    )


def test_spider_filters_discovery_to_backfill_auction_ids():
    spider = TajanSpider.__new__(TajanSpider)
    spider.auction_client = Mock()
    spider.should_skip_existing_auction = Mock(return_value=False)
    spider.backfill_auction_ids = {
        "tajan_target-wine-tuesday-january-2-2024-1100",
    }
    response = HtmlResponse(
        url="https://www.tajan.com/en/past/",
        request=Request(url="https://www.tajan.com/en/past/"),
        body=b"""
        <div id="plab__results-container">
          <div class="widget-event">
            <h2 class="event__title"><a href="https://www.tajan.com/en/auction/skipped/">Skipped Wine</a></h2>
            <div class="event__date">Monday, January 1, 2024</div>
            <div class="event__time mb-0">10:00</div>
            <div class="event__location mb-0">Paris, France</div>
          </div>
          <div class="widget-event">
            <h2 class="event__title"><a href="https://www.tajan.com/en/auction/target/">Target Wine</a></h2>
            <div class="event__date">Tuesday, January 2, 2024</div>
            <div class="event__time mb-0">11:00</div>
            <div class="event__location mb-0">Paris, France</div>
          </div>
        </div>
        """,
        encoding="utf-8",
    )

    results = asyncio.run(collect_async(spider.parse(response)))
    auction_items = [item for item in results if not isinstance(item, Request)]

    assert [item["external_id"] for item in auction_items] == [
        "tajan_target-wine-tuesday-january-2-2024-1100",
    ]
    assert len([item for item in results if isinstance(item, Request)]) == 1


def test_spider_detail_error_updates_progress_and_falls_back():
    spider = TajanSpider.__new__(TajanSpider)
    spider.progress_tracker = TajanProgressTracker()
    spider.progress_tracker.record_discovered_auction(
        "tajan_test-auction",
        "Test Auction",
        "https://www.tajan.com/en/auction/test",
    )
    spider.progress_tracker.complete_discovery()
    spider.progress_tracker.mark_started("tajan_test-auction")
    spider.progress_tracker.record_detail_request("tajan_test-auction")
    spider.yield_lot_from_listing_only = Mock(return_value=[])
    lot_item = LotItem()
    lot_item["auction_id"] = "tajan_test-auction"
    lot_item["external_id"] = "tajan_test-auction_1"
    failure = Mock()
    failure.request.meta = {"lot_item": lot_item, "auction_id": "tajan_test-auction"}
    failure.value = TimeoutError("boom")

    assert list(spider.parse_lot_detail_error(failure)) == []

    auction_progress = spider.progress_tracker.auction("tajan_test-auction")
    assert auction_progress.detail_errors == 1
    assert auction_progress.fallback == 1
    assert auction_progress.pending_detail == 0


def test_spider_start_and_auction_requests_wait_for_domcontentloaded_and_catalog_settles():
    spider = TajanSpider.__new__(TajanSpider)

    [start_request] = list(spider.start_requests())
    assert start_request.meta["allow_offsite"] is True
    assert start_request.meta["playwright_context"] == "tajan"
    assert start_request.meta["playwright_page_goto_kwargs"]["wait_until"] == "domcontentloaded"

    request = Request(
        url="https://www.tajan.com/en/auction/2531-wines-spirits/",
        meta={"auction_id": "tajan_test-auction"},
    )
    response = HtmlResponse(
        url=request.url,
        request=request,
        body=(
            b"<div class='sale-ctas'>"
            b"<a href='https://www.tajan.com/v1/auction-catalog/wine-and-spirit'>View lots</a>"
            b"</div>"
        ),
        encoding="utf-8",
    )

    [catalog_request] = list(spider.enter_auction_page(response))

    assert catalog_request.meta["allow_offsite"] is True
    assert catalog_request.meta["playwright_context"] == "tajan"
    assert catalog_request.meta["playwright_page_goto_kwargs"] == {
        "wait_until": "domcontentloaded",
        "timeout": 30000,
    }
    assert len(catalog_request.meta["playwright_page_methods"]) == 1
    assert catalog_request.meta["auction_id"] == "tajan_test-auction"
    assert catalog_request.errback == spider.parse_catalog_error


def test_spider_starts_backfill_from_existing_db_auction_url_without_discovery():
    spider = TajanSpider.__new__(TajanSpider)
    spider.backfill_auction_ids = {"tajan_existing-auction"}
    spider.progress_tracker = TajanProgressTracker()
    spider.auction_client = Mock()
    spider.auction_client.get_by_external_id.return_value = SimpleNamespace(
        external_id="tajan_existing-auction",
        auction_title="Existing Tajan Auction",
        url="https://www.tajan.com/en/auction/existing-tajan-auction/",
    )

    [request] = list(spider.start_requests())

    assert request.url == "https://www.tajan.com/en/auction/existing-tajan-auction/"
    assert request.callback == spider.enter_auction_page
    assert request.meta["auction_id"] == "tajan_existing-auction"
    assert request.meta["playwright"] is True
    assert request.meta["allow_offsite"] is True
    assert spider.auction_client.get_by_external_id.call_args.args == ("tajan_existing-auction",)
    assert spider.progress_tracker.total_auctions == 1
    assert spider.progress_tracker.discovery_complete is True


def test_spider_uses_discovery_when_backfill_auction_has_no_db_url():
    spider = TajanSpider.__new__(TajanSpider)
    spider.backfill_auction_ids = {"tajan_missing-auction"}
    spider.progress_tracker = TajanProgressTracker()
    spider.auction_client = Mock()
    spider.auction_client.get_by_external_id.return_value = SimpleNamespace(
        external_id="tajan_missing-auction",
        auction_title="Missing URL Auction",
        url=None,
    )

    [request] = list(spider.start_requests())

    assert request.url == "https://www.tajan.com/en/past/"
    assert request.callback == spider.parse


def test_spider_uses_conservative_tajan_rate_limit_settings():
    settings = TajanSpider.custom_settings

    assert settings["CONCURRENT_REQUESTS"] <= 2
    assert settings["CONCURRENT_REQUESTS_PER_DOMAIN"] <= 2
    assert settings["PLAYWRIGHT_MAX_PAGES_PER_CONTEXT"] <= 2
    assert settings["AUTOTHROTTLE_ENABLED"] is True
    assert 429 in settings["RETRY_HTTP_CODES"]
    assert settings["RETRY_TIMES"] == 3


def test_tajan_proxy_entry_accepts_host_port_username_password_format():
    proxy = parse_tajan_proxy_entry("31.59.20.176:6754:user:pass")

    assert proxy == {
        "server": "http://31.59.20.176:6754",
        "username": "user",
        "password": "pass",
    }


def test_tajan_proxy_contexts_are_created_for_each_proxy_entry():
    contexts = build_tajan_proxy_contexts(
        "\n".join(
            [
                "31.59.20.176:6754:user:pass",
                "http://other-user:other-pass@31.56.127.193:7684",
            ]
        )
    )

    assert contexts == {
        "tajan_proxy_0": {
            "proxy": {
                "server": "http://31.59.20.176:6754",
                "username": "user",
                "password": "pass",
            }
        },
        "tajan_proxy_1": {
            "proxy": {
                "server": "http://31.56.127.193:7684",
                "username": "other-user",
                "password": "other-pass",
            }
        },
    }


def test_tajan_playwright_meta_uses_one_sticky_proxy_context_by_default(monkeypatch):
    monkeypatch.delenv("TAJAN_PROXY_ROTATION", raising=False)
    spider = TajanSpider.__new__(TajanSpider)
    spider.playwright_context_specs = (
        ("tajan_proxy_0", {"proxy": {"server": "http://31.59.20.176:6754"}}),
        ("tajan_proxy_1", {"proxy": {"server": "http://31.56.127.193:7684"}}),
    )
    spider._playwright_context_index = 0

    assert spider.playwright_meta()["playwright_context"] == "tajan_proxy_0"
    assert spider.playwright_meta()["playwright_context"] == "tajan_proxy_0"
    assert spider.playwright_meta()["playwright_context"] == "tajan_proxy_0"


def test_tajan_playwright_meta_can_rotate_proxy_contexts_when_enabled(monkeypatch):
    monkeypatch.setenv("TAJAN_PROXY_ROTATION", "request")
    spider = TajanSpider.__new__(TajanSpider)
    spider.playwright_context_specs = (
        ("tajan_proxy_0", {"proxy": {"server": "http://31.59.20.176:6754"}}),
        ("tajan_proxy_1", {"proxy": {"server": "http://31.56.127.193:7684"}}),
    )
    spider._playwright_context_index = 0

    assert spider.playwright_meta()["playwright_context"] == "tajan_proxy_0"
    assert spider.playwright_meta()["playwright_context"] == "tajan_proxy_1"
    assert spider.playwright_meta()["playwright_context"] == "tajan_proxy_0"


def test_spider_skips_catalogue_pdf_when_selecting_tajan_catalog_link():
    spider = TajanSpider.__new__(TajanSpider)
    request = Request(
        url="https://www.tajan.com/en/auction/wine-1429/",
        meta={"auction_id": "tajan_fine-wine-thursday-september-15-2022-130-pm-cest"},
    )
    response = HtmlResponse(
        url=request.url,
        request=request,
        body=(
            b"<div class='sale-ctas'>"
            b"<a href='https://image.invaluable.com/privatelabel/tajan/wp-content/uploads/2022/09/TAJ-Vins.pdf'>"
            b"CATALOGUE PDF"
            b"</a>"
            b"<a href='https://www.tajan.com/auction-catalog/wines_KM4T6QFLVG'>VIEW LOTS</a>"
            b"<a href='https://www.tajan.com/auction-catalog/wines_KM4T6QFLVG'>BID ONLINE</a>"
            b"</div>"
        ),
        encoding="utf-8",
    )

    [catalog_request] = list(spider.enter_auction_page(response))

    assert catalog_request.url == (
        "https://www.tajan.com/auction-catalog/wines_KM4T6QFLVG"
        "?displayNum=180&pageNum=1"
    )


def test_spider_catalog_url_merges_existing_query_params():
    spider = TajanSpider.__new__(TajanSpider)

    result = spider.build_catalog_url(
        "https://www.tajan.com/v1/auction-catalog/vins-et-spiritueux_5V78C7HPMT?pageNum=1"
    )

    assert result == (
        "https://www.tajan.com/v1/auction-catalog/vins-et-spiritueux_5V78C7HPMT"
        "?pageNum=1&displayNum=180"
    )
    assert result.count("?") == 1


def test_spider_preserves_display_num_when_following_catalog_pagination():
    spider = TajanSpider.__new__(TajanSpider)
    request = Request(
        url=(
            "https://www.tajan.com/v1/auction-catalog/wines_KM4T6QFLVG"
            "?displayNum=180&pageNum=1"
        ),
        meta={"auction_id": "tajan_test-auction", "catalog_empty_retries": 2},
    )
    response = HtmlResponse(
        url=request.url,
        request=request,
        body=(
            b"<ol class='pagination justify-content-center'>"
            b"<li><a href='#'>1</a></li>"
            b"<li><a href='https://www.tajan.com/auction-catalog/wines_KM4T6QFLVG?pageNum=2'>"
            b">"
            b"</a></li>"
            b"</ol>"
        ),
        encoding="utf-8",
    )

    [next_page_request] = list(spider.parse_auction_page(response))

    assert next_page_request.url == (
        "https://www.tajan.com/auction-catalog/wines_KM4T6QFLVG"
        "?pageNum=2&displayNum=180"
    )


def test_spider_retries_empty_catalog_page_before_following_pagination():
    spider = TajanSpider.__new__(TajanSpider)
    spider.progress_tracker = TajanProgressTracker()
    request = Request(
        url=(
            "https://www.tajan.com/v1/auction-catalog/wines_KM4T6QFLVG"
            "?displayNum=180&pageNum=2"
        ),
        meta={"auction_id": "tajan_test-auction"},
    )
    response = HtmlResponse(
        url=request.url,
        request=request,
        body=(
            b"<ol class='pagination justify-content-center'>"
            b"<li><a href='https://www.tajan.com/auction-catalog/wines_KM4T6QFLVG?pageNum=3'>"
            b">"
            b"</a></li>"
            b"</ol>"
        ),
        encoding="utf-8",
    )

    [retry_request] = list(spider.parse_auction_page(response))

    assert retry_request.url == response.url
    assert retry_request.dont_filter is True
    assert retry_request.meta["catalog_empty_retries"] == 1
    assert retry_request.meta["auction_id"] == "tajan_test-auction"
