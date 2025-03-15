import json
import requests
from database import DatabaseClient, LotModel

BASE_URL = 'http://localhost:5000'

class TestLwinMatching:
    def __init__(self):
        self.database_client = DatabaseClient()
    
    def get_record_from_database(self):
        lot_item = self.database_client.get_random_item(LotModel)
        params_string = self.create_params_string(lot_item)
        return lot_item, params_string

    def create_params_string(self, lot_item):
        params = {
            'wine_name': lot_item.wine_name,
            'lot_producer': lot_item.lot_producer,
            'region': lot_item.region,
            'sub_region': lot_item.sub_region,
            'country': lot_item.country,
            'colour': lot_item.wine_type
        }
        return json.dumps(params)
    
    def test_lwin_matching(self, params_string):
        response = requests.get(f'{BASE_URL}/match', params=json.loads(params_string))
        return response.json()

if __name__ == '__main__':
    test = TestLwinMatching()
    lot_item, params_string = test.get_record_from_database()
    result = test.test_lwin_matching(params_string)
    print(params_string)
    print(result)
    