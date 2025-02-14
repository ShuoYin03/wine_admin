from database_client import DatabaseClient

db_client = DatabaseClient("wine_admin", "postgres", "341319")
db_client.connect()