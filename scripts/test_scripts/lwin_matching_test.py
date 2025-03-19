import json
import math
import requests
import pandas as pd
from database import DatabaseClient

BASE_URL = 'http://localhost:5000'

class TestLwinMatching:
    def __init__(self):
        self.database_client = DatabaseClient()
        self.df = pd.read_excel('../../files/LWIN & Auction match.xlsx', header=6)
    
    def test_lwin_matching(self):
        matching_results = []

        for index, row in self.df.iterrows():
            if isinstance(row['Top Lot (12 Btls Unless Stated)'], float) and math.isnan(row['Top Lot (12 Btls Unless Stated)']):
                continue
            
            payload = {
                'wine_name': row['Top Lot (12 Btls Unless Stated)'],
                'region': row['LWIN Region'],
            }
            response = requests.post(f'{BASE_URL}/match', json=payload)
            result = response.json()
            lwin_code = result['lwin_code']
            matched_wine_name = [match_item['display_name'] for match_item in result['match_item']]
            expected_lwin_code = row['Latest LWIN']
            match_status = result['matched']

            matching_results.append({
                'wine_name': row['Top Lot (12 Btls Unless Stated)'],
                'matched_wine_name': matched_wine_name,
                'matched_lwin_code': lwin_code,
                'expected_lwin_code': expected_lwin_code,
                'match_score': result['match_score'],
                'result': self.check_lwin_matched(lwin_code, expected_lwin_code, match_status, row['Match Status'])
            })

        true_count = sum(1 for result in matching_results if result['result'] is True)

        test_result = {
            'total': len(matching_results),
            'true_count': true_count,
            'matching_results': matching_results
        }

        with open('lwin_matching_results.json', 'w') as f:
            json.dump(test_result, f, indent=4)

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
    test.test_lwin_matching()
    