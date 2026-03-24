from __future__ import annotations

import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from itemadapter import ItemAdapter
from psycopg2.errors import ForeignKeyViolation
from sqlalchemy.exc import IntegrityError

sys.modules.setdefault("PyPDF2", Mock())

from wine_spider.items import LotDetailItem, LotItem
from wine_spider import pipelines


def make_spider():
    return SimpleNamespace(logger=Mock())


class BaseStoragePipelineTests(unittest.TestCase):
    def test_safe_upsert_queues_foreign_key_failures(self):
        pipeline = pipelines.BaseStoragePipeline()
        spider = make_spider()
        pipeline.open_spider(spider)

        def failing_write(_data):
            raise IntegrityError("stmt", "params", ForeignKeyViolation())

        inserted = pipeline.safe_upsert(
            failing_write,
            {"id": 1},
            spider,
            "test context",
        )

        self.assertFalse(inserted)
        self.assertEqual(len(pipeline._retry_queue), 1)

    def test_safe_upsert_reraises_non_foreign_key_integrity_errors(self):
        pipeline = pipelines.BaseStoragePipeline()
        spider = make_spider()
        pipeline.open_spider(spider)

        def failing_write(_data):
            raise IntegrityError("stmt", "params", Exception("boom"))

        with self.assertRaises(IntegrityError):
            pipeline.safe_upsert(failing_write, {"id": 1}, spider, "test context")

    def test_close_spider_retries_each_deferred_write_once(self):
        pipeline = pipelines.BaseStoragePipeline()
        spider = make_spider()
        pipeline.open_spider(spider)
        writer = Mock()
        pipeline._retry_queue.append((writer, {"id": 1}, "test context"))

        pipeline.close_spider(spider)

        writer.assert_called_once_with({"id": 1})
        self.assertEqual(pipeline._retry_queue, [])


class LotPipelineTests(unittest.TestCase):
    def setUp(self):
        self.spider = make_spider()
        self.pipeline = pipelines.LotPipeline()
        self.pipeline.open_spider(self.spider)

    @patch.object(pipelines.lot_items_client, "upsert_by_external_id")
    @patch.object(pipelines.lot_items_client, "delete_by_external_id")
    @patch.object(pipelines.lots_client, "upsert_by_external_id")
    def test_lot_then_detail_writes_detail_immediately(self, lots_upsert, delete_items, detail_upsert):
        lot = LotItem(external_id="lot-1", auction_id="auction-1")
        detail = LotDetailItem(lot_id="lot-1", lot_producer="Producer A")

        self.pipeline.process_item(lot, self.spider)
        self.pipeline.process_item(detail, self.spider)

        lots_upsert.assert_called_once_with(ItemAdapter(lot).asdict())
        delete_items.assert_called_once_with("lot-1")
        detail_upsert.assert_called_once_with(ItemAdapter(detail).asdict())

    @patch.object(pipelines.lot_items_client, "upsert_by_external_id")
    @patch.object(pipelines.lot_items_client, "delete_by_external_id")
    @patch.object(pipelines.lots_client, "upsert_by_external_id")
    def test_detail_then_lot_flushes_pending_buffer(self, lots_upsert, delete_items, detail_upsert):
        detail = LotDetailItem(lot_id="lot-1", lot_producer="Producer A")
        lot = LotItem(external_id="lot-1", auction_id="auction-1")

        self.pipeline.process_item(detail, self.spider)
        self.pipeline.process_item(lot, self.spider)

        lots_upsert.assert_called_once_with(ItemAdapter(lot).asdict())
        delete_items.assert_called_once_with("lot-1")
        detail_upsert.assert_called_once_with(ItemAdapter(detail).asdict())
        self.assertNotIn("lot-1", self.pipeline._pending_details)

    @patch.object(pipelines.lot_items_client, "upsert_by_external_id")
    @patch.object(pipelines.lot_items_client, "delete_by_external_id")
    @patch.object(pipelines.lots_client, "upsert_by_external_id")
    def test_reprocessing_lot_deletes_old_details_before_rewrite(self, lots_upsert, delete_items, detail_upsert):
        lot = LotItem(external_id="lot-1", auction_id="auction-1")
        detail = LotDetailItem(lot_id="lot-1", lot_producer="Producer A")

        self.pipeline.process_item(lot, self.spider)
        self.pipeline.process_item(detail, self.spider)
        self.pipeline.process_item(lot, self.spider)

        self.assertEqual(lots_upsert.call_count, 2)
        self.assertEqual(delete_items.call_count, 2)
        detail_upsert.assert_called_once_with(ItemAdapter(detail).asdict())

    def test_close_spider_logs_orphaned_pending_details(self):
        detail = LotDetailItem(lot_id="lot-1", lot_producer="Producer A")
        self.pipeline.process_item(detail, self.spider)

        self.pipeline.close_spider(self.spider)

        self.spider.logger.error.assert_called()


class AuctionSalesAggregatorPipelineTests(unittest.TestCase):
    def setUp(self):
        self.spider = make_spider()
        self.pipeline = pipelines.AuctionSalesAggregatorPipeline()
        self.pipeline.open_spider(self.spider)

    def test_aggregator_uses_first_non_null_currency_and_counts_all_estimates(self):
        self.pipeline.process_item(
            LotItem(
                external_id="lot-1",
                auction_id="auction-1",
                original_currency="USD",
                low_estimate=100,
                high_estimate=200,
                sold=False,
            ),
            self.spider,
        )
        self.pipeline.process_item(
            LotItem(
                external_id="lot-2",
                auction_id="auction-1",
                original_currency=None,
                low_estimate=300,
                high_estimate=400,
                sold=True,
                end_price=350,
                volume=1.5,
            ),
            self.spider,
        )

        stats = self.pipeline.auction_sales["auction-1"]
        self.assertEqual(stats["currency"], "USD")
        self.assertEqual(stats["total_low_estimate"], 400)
        self.assertEqual(stats["total_high_estimate"], 600)
        self.assertEqual(stats["total_sales"], 350)

    def test_single_cellar_skips_null_producers(self):
        self.pipeline.process_item(
            LotItem(external_id="lot-1", auction_id="auction-1", sold=False),
            self.spider,
        )
        self.pipeline.process_item(LotDetailItem(lot_id="lot-1", lot_producer=None), self.spider)
        self.pipeline.process_item(LotDetailItem(lot_id="lot-1", lot_producer="Producer A"), self.spider)
        self.pipeline.process_item(LotDetailItem(lot_id="lot-1", lot_producer="Producer B"), self.spider)

        stats = self.pipeline.auction_sales["auction-1"]
        self.assertEqual(stats["single_cellar_check"], "Producer A")
        self.assertFalse(stats["single_cellar"])

    @patch.object(pipelines.auction_sales_client, "upsert_by_external_id")
    def test_close_spider_does_not_emit_value_sold(self, auction_sales_upsert):
        self.pipeline.process_item(
            LotItem(
                external_id="lot-1",
                auction_id="auction-1",
                original_currency="USD",
                low_estimate=100,
                high_estimate=200,
                sold=True,
                end_price=250,
                volume=1.0,
            ),
            self.spider,
        )

        self.pipeline.close_spider(self.spider)

        saved_data = auction_sales_upsert.call_args.args[0]
        self.assertNotIn("value_sold", saved_data)
        self.assertEqual(saved_data["total_sales"], 250)


if __name__ == "__main__":
    unittest.main()
