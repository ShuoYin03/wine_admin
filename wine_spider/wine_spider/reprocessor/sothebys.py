import os
import pandas as pd
from database import DatabaseClient
from wine_spider.wine_spider.helpers import parse_volumn_and_unit_from_title, match_lot_info, region_to_country
from wine_spider.wine_spider.exceptions import (
    NoPreDefinedVolumeIdentifierException,
    AmbiguousRegionAndCountryMatchException,
    NoMatchedRegionAndCountryException,
)

class SothebysReprocessor:
    def __init__(self):
        self.db_client = DatabaseClient()
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.lwin_df = pd.read_excel(os.path.join(base_dir, "..", "spiders", "LWIN wines.xls"))

    def reprocess(self):
        failed_items = self.db_client.query_items(
            table_name="failed_lots"
        )

        print(f"Total failed items: {len(failed_items)}")

        for item in failed_items:
            item_id = item.get("id")
            try:
                item['volumn'], item['unit'] = parse_volumn_and_unit_from_title(item['wine_name'])
                if not item['lot_producer'] and 'Spirits' not in item['lot_type'] or not item['region'] or not item['country']:
                    lot_info = match_lot_info(item['wine_name'], self.lwin_df)
                    item['lot_producer'] = [lot_info[0]] if not item['lot_producer'] else item['lot_producer']
                    item['region'] = lot_info[1] if not item['region'] else item['region']
                    item['sub_region'] = lot_info[2]
                    item['country'] = lot_info[3] if not item['country'] else item['country']

                self.db_client.insert_item(
                    table_name="lots",
                    item_data=item,
                )

                self.db_client.delete_item(
                    table_name="failed_lots",
                    item_id=item_id,
                )
                
            except Exception as e:
                if isinstance(e, AmbiguousRegionAndCountryMatchException) or isinstance(e, NoMatchedRegionAndCountryException):
                    if 'region' in item and item["region"]:
                        try:
                            item["country"] = region_to_country(item["region"]) if 'country' not in item and not item["country"] else item["country"]

                            self.db_client.insert_item(
                                table_name="lots",
                                item_data=item,
                            )

                            self.db_client.delete_item(
                                table_name="failed_lots",
                                item_id=item_id,
                            )
                            
                        except Exception as e:
                            print(f"Failed to find country for region: {item['region']} Error: {e}")
                            continue

                print(f"Failed to reprocess item with ID: {item_id} Error: {e}")

SothebysReprocessor().reprocess()