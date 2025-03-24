import json
import math
import aiohttp
import asyncio
import pandas as pd
from database import DatabaseClient

BASE_URL = 'http://localhost:5000'

class TestLwinMatching:
    def __init__(self):
        self.database_client = DatabaseClient()
        self.df = pd.read_excel('../../files/LWIN & Auction match.xlsx', header=6)
    
    async def test_lwin_matching(self):
        matching_results = []

        async with aiohttp.ClientSession() as session:
            tasks = []
            for index, row in self.df.iterrows():
                if isinstance(row['Top Lot (12 Btls Unless Stated)'], float) and math.isnan(row['Top Lot (12 Btls Unless Stated)']):
                    continue

                payload = {
                    'wine_name': row['Top Lot (12 Btls Unless Stated)'],
                    'region': row['LWIN Region'],
                }

                tasks.append(self.fetch_match(session, payload, row))

            results = await asyncio.gather(*tasks)

            matching_results.extend(results)

        true_count = sum(1 for result in matching_results if result['result'] is True)

        test_result = {
            'total': len(matching_results),
            'true_count': true_count,
            'matching_results': matching_results
        }

        with open('lwin_matching_results.json', 'w') as f:
            json.dump(test_result, f, indent=4)

        print(f'Test finished: {true_count}/{len(matching_results)} matched.')

    async def fetch_match(self, session, payload, row):
        url = f'{BASE_URL}/match'
        try:
            async with session.post(url, json=payload) as response:
                result = await response.json()

                lwin_code = result['lwin_code']
                matched_wine_name = [match_item['display_name'] for match_item in result['match_item']]
                expected_lwin_code = row['Latest LWIN']
                match_status = result['matched']

                return {
                    'wine_name': row['Top Lot (12 Btls Unless Stated)'],
                    'matched_wine_name': matched_wine_name,
                    'matched_lwin_code': lwin_code,
                    'expected_lwin_code': expected_lwin_code,
                    'match_score': result['match_score'],
                    'result': self.check_lwin_matched(lwin_code, expected_lwin_code, match_status, row['Match Status'])
                }
            
        except Exception as e:
            print(f"Error fetching data for payload: {payload} - Error: {e}")
            return {
                'wine_name': row['Top Lot (12 Btls Unless Stated)'],
                'matched_wine_name': [],
                'matched_lwin_code': [],
                'expected_lwin_code': row['Latest LWIN'],
                'match_score': [],
                'result': False
            }

    def check_lwin_matched(self, lwin_codes, expected_lwin_code, match_status, expected_match_status):
        if match_status == 'exact_match' and expected_match_status == 'EXACT_MATCHED':
            for lwin_code in lwin_codes:
                if lwin_code in expected_lwin_code:
                    return True
            return False
        elif match_status == 'multi_match':
            for lwin_code in lwin_codes:
                if lwin_code in expected_lwin_code:
                    return True
            return False
        elif match_status == 'not_match' and expected_match_status == 'NOT_MATCHED':
            if not lwin_codes or lwin_codes == []:
                return True
            return False
        elif match_status == 'exact_match' and expected_match_status == 'NOT_MATCHED':
            for lwin_code in lwin_codes:
                if lwin_code in expected_lwin_code:
                    return True
            return False
        elif match_status == 'not_match' and expected_match_status == 'EXACT_MATCHED':
            return False
        else:
            print(f'Unexpected match status: {match_status}')
            print(f'Expected match status: {expected_match_status}')

if __name__ == '__main__':
    test = TestLwinMatching()
    asyncio.run(test.test_lwin_matching())
    