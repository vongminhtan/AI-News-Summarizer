import json
from database_manager import get_db

def diagnose_articles():
    print("--- 🩺 Diagnosing Articles Table ---")
    
    with get_db() as conn:
        with conn.cursor() as cur:
            # 1. Check Status Distribution
            cur.execute("SELECT status, COUNT(*) FROM articles GROUP BY status")
            stats = cur.fetchall()
            print("\n📊 Status Distribution:")
            for s, c in stats:
                print(f"   - {s}: {c}")

            # 2. Check for Strange Content (Empty but status='scraped' or 'analyzed')
            print("\n🔍 Checking for Missing Content (Status = scraped/analyzed):")
            cur.execute("""
                SELECT url, title, status, length(content) 
                FROM articles 
                WHERE status IN ('scraped', 'analyzed') AND (content IS NULL OR content = '')
            """)
            bad_content = cur.fetchall()
            if bad_content:
                for row in bad_content:
                    print(f"   ❌ Empty Content: {row[0]} [Status: {row[2]}]")
            else:
                print("   ✅ All scraped/analyzed articles have content.")

            # 3. Check for Malformed/Empty Tags (Status = analyzed)
            print("\n🔍 Checking for Missing/Invalid Tags (Status = analyzed):")
            cur.execute("""
                SELECT url, title, tags 
                FROM articles 
                WHERE status = 'analyzed'
            """)
            analyzed = cur.fetchall()
            
            for url, title, tags in analyzed:
                # tags is already a dict/list if using psycopg2 with jsonb, or string
                if not tags:
                    print(f"   ❌ Null Tags: {title}")
                    continue
                
                # Check critical fields
                if isinstance(tags, str):
                    try:
                        tags = json.loads(tags)
                    except:
                        print(f"   ❌ Invalid JSON Tags: {title}")
                        continue
                
                if not isinstance(tags, dict):
                    print(f"   ❌ Tags is not a dict: {title} ({type(tags)})")
                    continue
                    
                missing_fields = []
                for field in ['sentiment', 'sectors']:
                    if field not in tags:
                        missing_fields.append(field)
                
                if missing_fields:
                    print(f"   ⚠️ Malformed Tags {missing_fields}: {title}")

if __name__ == "__main__":
    diagnose_articles()
