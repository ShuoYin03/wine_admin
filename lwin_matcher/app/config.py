class Config:
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'postgresql://user:password@localhost:5432/your_database'
    SQLALCHEMY_TRACK_MODIFICATIONS = False