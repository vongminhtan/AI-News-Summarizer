from database_manager import get_db

def fix_data():
    print("--- 🔧 Fixing Data Anomalies ---")
    
    with get_db() as conn:
        with conn.cursor() as cur:
            # 1. Reset 'analyzed'/'scraped' items with empty content back to 'filtered_in'
            # This forces Step 3 to re-scrape them.
            print("1. Resetting articles with empty content...")
            cur.execute("""
                UPDATE articles 
                SET status = 'filtered_in' 
                WHERE status IN ('scraped', 'analyzed') 
                  AND (content IS NULL OR content = '' OR content = 'From JSON Migration')
            """)
            print(f"   ✅ Reset {cur.rowcount} articles to 'filtered_in'.")
            
            # 2. Reset 'analyzed' items with NULL tags back to 'scraped'
            # This forces Step 4 to re-analyze them.
            print("2. Resetting articles with missing tags...")
            cur.execute("""
                UPDATE articles
                SET status = 'scraped'
                WHERE status = 'analyzed' AND (tags IS NULL OR tags::text = '{}')
            """)
            print(f"   ✅ Reset {cur.rowcount} articles to 'scraped'.")

            conn.commit()

if __name__ == "__main__":
    fix_data()
