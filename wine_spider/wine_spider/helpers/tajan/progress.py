from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class TajanAuctionCandidate:
    auction_id: str
    title: str
    url: str


@dataclass
class TajanAuctionProgress:
    auction_id: str
    title: str = ""
    url: str = ""
    queued: bool = False
    active: bool = False
    skipped: bool = False
    completed: bool = False
    failed: bool = False
    catalog_complete: bool = False
    catalog_pages_seen: int = 0
    catalog_total_pages: int | None = None
    lots_seen: int = 0
    detail_requests: int = 0
    detail_success: int = 0
    listing_only: int = 0
    fallback: int = 0
    detail_errors: int = 0
    pending_detail: int = 0
    next_lot_log_at: int = 100
    last_lot_log_time: float = 0.0


class TajanProgressTracker:
    def __init__(self, log_every_lots: int = 100, log_every_seconds: int = 60):
        self.log_every_lots = log_every_lots
        self.log_every_seconds = log_every_seconds
        self.past_pages = 0
        self.page_auctions_seen = 0
        self.discovery_complete = False
        self.candidates: list[TajanAuctionCandidate] = []
        self.auctions: dict[str, TajanAuctionProgress] = {}

    @property
    def total_auctions(self) -> int:
        return len(self.candidates)

    def record_discovery_page(
        self,
        page_url: str,
        page_auctions: int,
        wine_candidates: int,
        has_next_page: bool,
    ) -> None:
        self.past_pages += 1
        self.page_auctions_seen += page_auctions
        self._last_discovery_page_url = page_url
        self._last_discovery_page_auctions = page_auctions
        self._last_discovery_wine_candidates = wine_candidates
        self._last_discovery_has_next_page = has_next_page

    def record_discovered_auction(
        self,
        auction_id: str,
        title: str,
        url: str,
    ) -> TajanAuctionCandidate:
        if auction_id in self.auctions:
            return TajanAuctionCandidate(auction_id, title, url)

        candidate = TajanAuctionCandidate(auction_id, title, url)
        self.candidates.append(candidate)
        self.auctions[auction_id] = TajanAuctionProgress(
            auction_id=auction_id,
            title=title,
            url=url,
            next_lot_log_at=self.log_every_lots,
        )
        return candidate

    def complete_discovery(self) -> None:
        self.discovery_complete = True

    def auction(self, auction_id: str) -> TajanAuctionProgress:
        if auction_id not in self.auctions:
            self.auctions[auction_id] = TajanAuctionProgress(
                auction_id=auction_id,
                next_lot_log_at=self.log_every_lots,
            )
        return self.auctions[auction_id]

    def mark_queued(self, auction_id: str) -> None:
        auction = self.auction(auction_id)
        auction.queued = True

    def mark_started(self, auction_id: str) -> None:
        auction = self.auction(auction_id)
        auction.active = True
        auction.queued = False
        if auction.last_lot_log_time == 0:
            auction.last_lot_log_time = time.monotonic()

    def mark_skipped(self, auction_id: str) -> None:
        auction = self.auction(auction_id)
        auction.skipped = True
        auction.active = False
        auction.queued = False

    def mark_failed(self, auction_id: str) -> None:
        auction = self.auction(auction_id)
        auction.failed = True
        auction.active = False
        auction.queued = False

    def mark_completed(self, auction_id: str) -> None:
        auction = self.auction(auction_id)
        auction.completed = True
        auction.active = False
        auction.queued = False

    def record_catalog_page(
        self,
        auction_id: str,
        page_url: str,
        page_lots: int,
        current_page: int | None,
        total_pages: int | None,
        has_next_page: bool,
    ) -> None:
        auction = self.auction(auction_id)
        auction.catalog_pages_seen += 1
        auction.lots_seen += page_lots
        if total_pages is not None:
            auction.catalog_total_pages = total_pages
        auction.catalog_complete = not has_next_page
        self._last_catalog_page_url = page_url
        self._last_catalog_current_page = current_page
        self._maybe_mark_completed(auction_id)

    def record_detail_request(self, auction_id: str) -> None:
        auction = self.auction(auction_id)
        auction.detail_requests += 1
        auction.pending_detail += 1
        auction.completed = False
        if not auction.failed and not auction.skipped:
            auction.active = True

    def record_listing_only(self, auction_id: str) -> None:
        auction = self.auction(auction_id)
        auction.listing_only += 1
        self._maybe_mark_completed(auction_id)

    def record_detail_success(self, auction_id: str) -> None:
        auction = self.auction(auction_id)
        auction.detail_success += 1
        auction.pending_detail = max(0, auction.pending_detail - 1)
        self._maybe_mark_completed(auction_id)

    def record_fallback(self, auction_id: str) -> None:
        auction = self.auction(auction_id)
        auction.fallback += 1
        auction.pending_detail = max(0, auction.pending_detail - 1)
        self._maybe_mark_completed(auction_id)

    def record_detail_error(self, auction_id: str) -> None:
        auction = self.auction(auction_id)
        auction.detail_errors += 1

    def should_log_lot_progress(
        self,
        auction_id: str,
        current_time: float | None = None,
    ) -> bool:
        auction = self.auction(auction_id)
        current_time = time.monotonic() if current_time is None else current_time
        if auction.lots_seen >= auction.next_lot_log_at:
            auction.next_lot_log_at += self.log_every_lots
            auction.last_lot_log_time = current_time
            return True
        if current_time - auction.last_lot_log_time >= self.log_every_seconds:
            auction.last_lot_log_time = current_time
            return True
        return False

    def discovery_log_line(self) -> str:
        return (
            "Tajan discovery: "
            f"past_pages={self.past_pages} "
            f"page_auctions={getattr(self, '_last_discovery_page_auctions', 0)} "
            f"wine_candidates={getattr(self, '_last_discovery_wine_candidates', 0)} "
            f"wine_auctions_found={self.total_auctions} "
            f"discovery_complete={self.discovery_complete}"
        )

    def auction_progress(self) -> dict[str, int | float]:
        completed = sum(1 for auction in self.auctions.values() if auction.completed)
        skipped = sum(1 for auction in self.auctions.values() if auction.skipped)
        active = sum(1 for auction in self.auctions.values() if auction.active)
        failed = sum(1 for auction in self.auctions.values() if auction.failed)
        done = completed + skipped + failed
        total = self.total_auctions
        remaining = max(0, total - done - active)
        progress = round((done / total * 100), 1) if total else 0.0
        return {
            "completed": completed,
            "skipped_existing": skipped,
            "active": active,
            "failed": failed,
            "remaining": remaining,
            "total": total,
            "progress": progress,
        }

    def auction_progress_log_line(self) -> str:
        progress = self.auction_progress()
        return (
            "Tajan auction progress: "
            f"completed={progress['completed']} "
            f"skipped_existing={progress['skipped_existing']} "
            f"active={progress['active']} "
            f"failed={progress['failed']} "
            f"remaining={progress['remaining']} "
            f"total={progress['total']} "
            f"progress={progress['progress']}%"
        )

    def catalog_progress_log_line(self, auction_id: str) -> str:
        auction = self.auction(auction_id)
        catalog_pages = str(auction.catalog_pages_seen)
        if auction.catalog_total_pages is not None:
            catalog_pages = f"{auction.catalog_pages_seen}/{auction.catalog_total_pages}"
        return (
            "Tajan catalog progress: "
            f"auction_id={auction_id} "
            f"catalog_pages={catalog_pages} "
            f"lots_seen={auction.lots_seen} "
            f"detail_requests={auction.detail_requests} "
            f"detail_success={auction.detail_success} "
            f"listing_only={auction.listing_only} "
            f"fallback={auction.fallback} "
            f"detail_errors={auction.detail_errors} "
            f"pending_detail={auction.pending_detail}"
        )

    def summary_log_line(self, reason: str) -> str:
        lots_seen = sum(auction.lots_seen for auction in self.auctions.values())
        detail_success = sum(auction.detail_success for auction in self.auctions.values())
        listing_only = sum(auction.listing_only for auction in self.auctions.values())
        fallback = sum(auction.fallback for auction in self.auctions.values())
        progress = self.auction_progress()
        return (
            "Tajan summary: "
            f"reason={reason} "
            f"total={progress['total']} "
            f"completed={progress['completed']} "
            f"skipped_existing={progress['skipped_existing']} "
            f"active={progress['active']} "
            f"failed={progress['failed']} "
            f"remaining={progress['remaining']} "
            f"progress={progress['progress']}% "
            f"lots_seen={lots_seen} "
            f"detail_success={detail_success} "
            f"listing_only={listing_only} "
            f"fallback={fallback}"
        )

    def _maybe_mark_completed(self, auction_id: str) -> None:
        auction = self.auction(auction_id)
        if auction.catalog_complete and auction.pending_detail == 0 and not auction.failed:
            self.mark_completed(auction_id)
