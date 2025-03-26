import json
import asyncio
import requests
from database.database_client import DatabaseClient

class DatabaseQueryTest:
    def __init__(self):
        self.base_url = 'http://localhost:5000'
        self.client = DatabaseClient()

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
    
    async def test_query_items(self):
        results = await self.client.query_items(
            table_name='lots',
            filters={
                'id': "0017d92c-01ba-4111-b22f-b22e216bcc60",
            }
        )
    
    async def test_query_items_through_api(self):
        payload = {
            'table': 'lots',
            'filters': {
                'id': "0017d92c-01ba-4111-b22f-b22e216bcc60",
            }
        }
        response = requests.get(f'{self.base_url}/query', json=payload)
        print(response)
        results = response.json()
        print(results)

if __name__ == '__main__':
    test = DatabaseQueryTest()
    asyncio.run(test.test_query_items_through_api())
