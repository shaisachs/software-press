import psycopg2
import os

def get_conn():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        dbname=os.getenv("POSTGRES_DB", "software_factory"),
        user=os.getenv("POSTGRES_USER", "sf_user"),
        password=os.getenv("POSTGRES_PASSWORD", "sf_password"),
    )