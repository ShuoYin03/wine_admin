from database.database_client import DatabaseClient
from app.model import MatchResult

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

        table_items = self.calculate_multiple(lwinMatchingParams, table_items)

        if len(table_items) == 0:
            match = MatchResult.NOT_MATCH
        elif len(table_items) == 1:
            match = MatchResult.MATCH
        else:
            match = MatchResult.MULTI_MATCH
            
        return match, [table_item.lwin for table_item in table_items]
    
    def calculate_multiple(self, lwinMatchingParams, table_items):
        max_score = (None, 0)

        for table_item in table_items:
            score = self.calculate_single(lwinMatchingParams, table_item)
            max_score = max(table_item, score)
        
        return max_score

    def calculate_single(self, lwinMatchingParams, table_item):
        # calculate a score or boolean
        pass
        
        
