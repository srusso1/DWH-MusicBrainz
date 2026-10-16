from pathlib import Path
import psycopg2
from dotenv import load_dotenv
import os

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

conn = psycopg2.connect(
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", "5435")),
    dbname=os.getenv("DB_NAME", "dw_musicbrainz"),
    user=os.getenv("DB_USER", "postgres"),
    password=os.getenv("DB_PASSWORD", "postgres123"),
)
cur = conn.cursor()
cur.execute("SELECT pid, state, wait_event_type, wait_event, query FROM pg_stat_activity WHERE state != 'idle';")
for r in cur.fetchall():
    print(f"PID: {r[0]} | State: {r[1]} | Wait: {r[2]}:{r[3]} | Query: {r[4][:60]}...")
cur.close()
conn.close()