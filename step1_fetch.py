import feedparser
import time
from datetime import datetime
import config
from database_manager import get_db

def fetch_rss():
    print(f"--- Đang quét {len(config.RSS_URLS)} nguồn RSS ---")
    if config.TEST_MODE:
        print(f"Chế độ TEST: Giới hạn {config.TEST_LIMIT} bài mỗi nguồn.")

    new_articles_count = 0
    total_articles = 0
    
    with get_db() as conn:
        with conn.cursor() as cur:
            for rss_url in config.RSS_URLS:
                feed = feedparser.parse(rss_url)
                print(f"[{rss_url}] Lấy được {len(feed.entries)} bài.")
                
                entries = feed.entries[:config.TEST_LIMIT] if config.TEST_MODE else feed.entries
                
                for entry in entries:
                    total_articles += 1
                    try:
                        # Chuẩn hóa dữ liệu
                        title = entry.get('title', 'No Title')
                        link = entry.get('link', '')
                        published_parsed = entry.get('published_parsed')
                        published_date = datetime.fromtimestamp(time.mktime(published_parsed)) if published_parsed else datetime.now()
                        source = rss_url

                        if not link: continue

                        # Upsert vào DB
                        # Nếu đã tồn tại nhưng status='fetched' thì cập nhật (VD: cập nhật title)
                        # Nếu status khác 'fetched' (đang xử lý) thì bỏ qua
                        cur.execute("""
                            INSERT INTO articles (url, title, source, published_date, status, created_at)
                            VALUES (%s, %s, %s, %s, 'fetched', NOW())
                            ON CONFLICT (url) DO NOTHING
                            RETURNING url;
                        """, (link, title, source, published_date))
                        
                        if cur.fetchone():
                            new_articles_count += 1
                            
                    except Exception as e:
                        print(f"⚠️ Lỗi xử lý bài: {e}")
                        continue
            
            conn.commit()

    print(f"✅ Đã cập nhật database: +{new_articles_count} bài mới (Tổng quét: {total_articles})")
    
    return total_articles, new_articles_count

if __name__ == "__main__":
    fetch_rss()