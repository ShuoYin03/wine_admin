import os

class EnvironmentHelper:
    def __init__(self):
        self.env = os.getenv('ENV', 'local')

    def get_matching_url(self):
        if self.env == 'local':
            return 'http://localhost:5000/match'
        else:
            return 'http://lwin-matcher:5000/match'