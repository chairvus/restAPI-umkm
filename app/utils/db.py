import psycopg2
from psycopg2.extras import RealDictCursor
from config import Config

# Function databaase connection
def get_db_connection():
    conn = psycopg2.connect(
        dbname='umkm',
        user='postgres',
        password='artha',
        host='localhost'
    )
    return conn
