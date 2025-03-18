import numpy as np
import pandas as pd
from app.model import MatchResult
from collections import OrderedDict
from .utils import LwinMatchingUtils
from database.database_client import DatabaseClient
from database.model import LwinDatabaseModel

class LwinMatchingService:
    def __init__(self):
        self.db = DatabaseClient()
        self.sess = self.db.Session()
        self.table = self.db.get_table('lwin_database')

        table_items = pd.read_sql(self.sess.query(self.table).statement, self.sess.bind)
        self.utils = LwinMatchingUtils(
            table_items
        )
        self.table_items = table_items

    def lwin_matching(self, lwinMatchingParams):
        matches = self.calculate_multiple(lwinMatchingParams)
        if len(matches) == 0:
            match_result = MatchResult.NOT_MATCH
        elif len(matches) == 1:
            match_result = MatchResult.EXACT_MATCH
        else:
            match_result = MatchResult.MULTI_MATCH
        
        columns = [column.name for column in LwinDatabaseModel.__table__.columns]
        return match_result, [match[0]['lwin'] for match in matches], [match[1] for match in matches], [OrderedDict({columns[i]: match[0].iloc[i] for i in range(len(columns))}) for match in matches]
     

    def calculate_multiple(self, lwinMatchingParams):
        wine_name_similarities = self.utils.calculate_tfidf_similarity(lwinMatchingParams.wine_name)
        producer_similarities = self.utils.calculate_tfidf_similarity(lwinMatchingParams.lot_producer) if lwinMatchingParams.lot_producer else wine_name_similarities
        total_scores = (wine_name_similarities * 0.7 + producer_similarities * 0.3)

        # self.output_to_csv(table_items, wine_name_similarities, producer_similarities, total_scores, lwinMatchingParams)

        max_score = total_scores.max()

        if max_score > 0.8:
            top_matches = self.table_items.iloc[np.where(total_scores == max_score)[0]]
            matches = [(row, max_score) for _, row in top_matches.iterrows()]
            return matches
        else:
            return []
    
    def output_to_csv(self, table_items, wine_name_similarities, producer_similarities, total_scores, lwinMatchingParams):
        debug_df = table_items.copy()
        del debug_df['status']
        del debug_df['country']
        del debug_df['region']
        del debug_df['sub_region']
        del debug_df['site']
        del debug_df['parcel']
        del debug_df['colour']
        del debug_df['type']
        del debug_df['sub_type']

        debug_df['wine_name_score'] = wine_name_similarities
        debug_df['producer_score'] = producer_similarities
        debug_df['total_score'] = total_scores

        debug_df['query_wine_name'] = lwinMatchingParams.wine_name
        debug_df['query_producer'] = lwinMatchingParams.lot_producer

        debug_df.to_csv('debug_output.csv', index=False)
        self.table_items.to_csv('lwin_database.csv', index=False)