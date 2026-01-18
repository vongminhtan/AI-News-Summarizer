import signal
import time
import concurrent.futures
from newspaper import Article, Config
from database_manager import get_db
import config

# Timeout handler
def handler(signum, frame):
    raise TimeoutError("Scraping timed out")

# Register signal
signal.signal(signal.SIGALRM, handler)

def scrape_single_url(url):
    """
    Hàm cào dữ liệu cho 1 URL (Chạy trong Thread).
    Không kết nối DB ở đây để tránh lỗi Tunnel.
    """
    try:
        # Newspaper Config
        news_config = Config()
        news_config.browser_user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        news_config.request_timeout = 10
        
        article = Article(url, config=news_config)
        article.download()
        article.parse()
        
        content = article.text
        if not content or len(content) < 100:
            return (url, None, "Content too short")
            
        return (url, content, None)
        
    except Exception as e:
        return (url, None, str(e))

def scrape_articles():
    print("\n--- [Step 3] Scraping Content (Parallel) ---")
    
    with get_db() as conn:
        with conn.cursor() as cur:
            # 1. Get articles that passed the filter
            cur.execute("SELECT url FROM articles WHERE status = 'filtered_in'")
            rows = cur.fetchall()
            
            if not rows:
                print("⚠️ Không có bài báo nào cần cào (status='filtered_in').")
                return []

            target_urls = [r[0] for r in rows]
            print(f"🚀 Bắt đầu cào {len(target_urls)} bài (5 threads)...")

            success_count = 0
            
            # 2. Run Parallel Scraping
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                results = list(executor.map(scrape_single_url, target_urls))
            
            # 3. Update DB Sequentially
            for url, content, error in results:
                if content:
                    try:
                        cur.execute("""
                            UPDATE articles 
                            SET content = %s, scraped_at = NOW(), status = 'scraped'
                            WHERE url = %s
                        """, (content, url))
                        success_count += 1
                        print(f"✅ Scraped: {url}")
                    except Exception as e:
                        print(f"❌ DB Error {url}: {e}")
                else:
                    print(f"⚠️ Failed {url}: {error}")
                    # Optional: Update status to 'failed' or keep 'filtered_in' to retry later
            
            conn.commit()
            print(f"🎉 Hoàn tất cào {success_count}/{len(target_urls)} bài.")
            return target_urls

if __name__ == "__main__":
    scrape_articles()