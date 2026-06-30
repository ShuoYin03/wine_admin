from unittest.mock import patch

from wine_spider.helpers.tajan.progress import TajanProgressTracker


def test_tracker_reports_discovery_total_after_completion():
    tracker = TajanProgressTracker()

    tracker.record_discovery_page(
        page_url="https://www.tajan.com/en/past/",
        page_auctions=24,
        wine_candidates=2,
        has_next_page=True,
    )
    tracker.record_discovered_auction("auction-1", "Wine Sale", "https://example.test/1")
    tracker.record_discovered_auction("auction-2", "Spirits Sale", "https://example.test/2")
    tracker.complete_discovery()

    assert tracker.total_auctions == 2
    assert tracker.discovery_complete is True
    assert tracker.discovery_log_line().startswith("Tajan discovery:")
    assert "past_pages=1" in tracker.discovery_log_line()
    assert "wine_auctions_found=2" in tracker.discovery_log_line()
    assert "discovery_complete=True" in tracker.discovery_log_line()


def test_tracker_counts_skipped_completed_and_remaining_auctions():
    tracker = TajanProgressTracker()
    tracker.record_discovered_auction("auction-1", "Wine Sale", "https://example.test/1")
    tracker.record_discovered_auction("auction-2", "Spirits Sale", "https://example.test/2")
    tracker.record_discovered_auction("auction-3", "Fine Wine", "https://example.test/3")
    tracker.complete_discovery()

    tracker.mark_skipped("auction-1")
    tracker.mark_queued("auction-2")
    tracker.mark_started("auction-2")
    tracker.mark_completed("auction-2")

    assert tracker.auction_progress() == {
        "completed": 1,
        "skipped_existing": 1,
        "active": 0,
        "failed": 0,
        "remaining": 1,
        "total": 3,
        "progress": 66.7,
    }
    assert "completed=1" in tracker.auction_progress_log_line()
    assert "skipped_existing=1" in tracker.auction_progress_log_line()
    assert "remaining=1" in tracker.auction_progress_log_line()
    assert "progress=66.7%" in tracker.auction_progress_log_line()


def test_tracker_completes_auction_when_catalog_done_and_pending_detail_is_zero():
    tracker = TajanProgressTracker()
    tracker.record_discovered_auction("auction-1", "Wine Sale", "https://example.test/1")
    tracker.complete_discovery()
    tracker.mark_queued("auction-1")
    tracker.mark_started("auction-1")

    tracker.record_catalog_page(
        "auction-1",
        page_url="https://example.test/catalog?pageNum=1",
        page_lots=2,
        current_page=1,
        total_pages=1,
        has_next_page=False,
    )
    tracker.record_detail_request("auction-1")
    tracker.record_listing_only("auction-1")

    assert tracker.auction_progress()["completed"] == 0
    assert tracker.auction("auction-1").pending_detail == 1

    tracker.record_detail_success("auction-1")

    auction = tracker.auction("auction-1")
    assert auction.pending_detail == 0
    assert auction.completed is True
    assert tracker.auction_progress()["completed"] == 1
    assert "catalog_pages=1/1" in tracker.catalog_progress_log_line("auction-1")
    assert "lots_seen=2" in tracker.catalog_progress_log_line("auction-1")
    assert "detail_success=1" in tracker.catalog_progress_log_line("auction-1")
    assert "listing_only=1" in tracker.catalog_progress_log_line("auction-1")


def test_tracker_does_not_time_log_immediately_after_auction_starts():
    tracker = TajanProgressTracker(log_every_lots=100, log_every_seconds=60)
    tracker.record_discovered_auction("auction-1", "Wine Sale", "https://example.test/1")

    with patch("wine_spider.helpers.tajan.progress.time.monotonic", return_value=1000):
        tracker.mark_started("auction-1")

    assert tracker.should_log_lot_progress("auction-1", current_time=1001) is False
    assert tracker.should_log_lot_progress("auction-1", current_time=1061) is True
