from database_manager import get_db
import config
from datetime import datetime, timedelta

def check_db():
    print("--- Articles from last 24h ---")
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT status, count(*) 
                FROM articles 
                WHERE published_date >= (NOW() AT TIME ZONE 'UTC') - INTERVAL '24 hours'
                GROUP BY status
            """)
            counts = cur.fetchall()
            print("Status counts (last 24h):", counts)
            
            cur.execute("""
                SELECT url, title, status, published_date 
                FROM articles 
                WHERE published_date >= (NOW() AT TIME ZONE 'UTC') - INTERVAL '24 hours'
                ORDER BY published_date DESC 
                LIMIT 20
            """)
            rows = cur.fetchall()
            for r in rows:
                print(f"Status: {r[2]} | Date: {r[3]} | Title: {r[1][:50]}")

if __name__ == "__main__":
    check_db()
