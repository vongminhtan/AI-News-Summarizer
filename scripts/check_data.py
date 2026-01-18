from database_manager import get_db
import json

def query_data():
    print("--- QUERYING DATA FROM ARTICLES ---")
    try:
        with get_db() as conn:
            cur = conn.cursor()
            
            # Check articles count
            cur.execute("SELECT COUNT(*) FROM articles;")
            count = cur.fetchone()[0]
            print(f"Total articles: {count}")
            
            # Fetch last 3 analyzed articles
            cur.execute("""
                SELECT title, source, status, summary, tags 
                FROM articles 
                WHERE status = 'analyzed' 
                ORDER BY created_at DESC 
                LIMIT 3;
            """)
            rows = cur.fetchall()
            
            for i, row in enumerate(rows):
                print(f"\n--- Article {i+1} ---")
                print(f"Title: {row[0]}")
                print(f"Source: {row[1]}")
                print(f"Status: {row[2]}")
                print(f"Summary: {row[3][:100]}...")
                print(f"Tags: {json.dumps(row[4], ensure_ascii=False, indent=2)}")

            # Check daily insights
            cur.execute("SELECT date, hot_topics FROM daily_insights ORDER BY date DESC LIMIT 1;")
            insight = cur.fetchone()
            if insight:
                print(f"\n--- Latest Daily Insight ({insight[0]}) ---")
                print(f"Hot Topics: {json.dumps(insight[1], ensure_ascii=False, indent=2)}")
                
            cur.close()
    except Exception as e:
        print(f"❌ Lỗi: {e}")

if __name__ == "__main__":
    query_data()
