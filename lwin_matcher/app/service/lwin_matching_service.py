from rapidfuzz import fuzz
from app.model import MatchResult
from database.database_client import DatabaseClient

class LwinMatchingService:
    def __init__(self):
        self.db = DatabaseClient()
        
    def lwin_matching(self, lwinMatchingParams):
        table = self.db.get_table('lwin_database')
        table_items = self.db.sess.query(table)

        table_items = table_items.filter(
            table.c.country == lwinMatchingParams.country,
            table.c.region == lwinMatchingParams.region,
            table.c.sub_region == lwinMatchingParams.sub_region,
            table.c.colour == lwinMatchingParams.colour,
        ).all()

        matches = self.calculate_multiple(lwinMatchingParams, table_items)

        if len(matches) == 0:
            match_result = MatchResult.NOT_MATCH
        elif len(matches) == 1:
            match_result = MatchResult.EXACT_MATCH
        else:
            match_result = MatchResult.MULTI_MATCH
            
        return match_result, [match[0].lwin for match in matches], [match[1] for match in matches], [list(match[0]) for match in matches]
    
    def calculate_multiple(self, lwinMatchingParams, table_items):
        matches = []
        max_score = (None, 0)
        for table_item in table_items:
            score = self.calculate_single(lwinMatchingParams, table_item)
            if score[1] > max_score[1]:
                matches = [score]
            elif score[1] == max_score[1]:
                matches.append(score)
            max_score = max(max_score, score, key=lambda x: x[1])
        
        return matches

    def calculate_single(self, lwinMatchingParams, table_item):
        producer_title = table_item.producer_title.lower() if table_item.producer_title else ''
        producer_name = table_item.producer_name.lower() if table_item.producer_name else ''
        wine_name = table_item.display_name.lower() if table_item.display_name else ''
        wine = table_item.wine.lower() if table_item.wine else ''
        
        producer = producer_title + producer_name if producer_title else producer_name
        
        score_producer = fuzz.partial_ratio(lwinMatchingParams.producer, producer)
        score_wine_name = fuzz.partial_ratio(lwinMatchingParams.name, wine_name)
        score_wine = fuzz.partial_ratio(lwinMatchingParams.name, wine)

        # print all three scores
        print(score_producer, score_wine_name, score_wine)
        total_score = (score_producer + score_wine_name + score_wine) / 3

        return (table_item, total_score)
        
        
        
