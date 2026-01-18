import signal
import time
import concurrent.futures
from newspaper import Article, Config
from database_manager import get_db
import config
import random

# Timeout handler
def handler(signum, frame):
    raise TimeoutError("Scraping timed out")

# Register signal
signal.signal(signal.SIGALRM, handler)

import requests

def scrape_single_url(url):
    """
    Hàm cào dữ liệu cho 1 URL (Chạy trong Thread).
    Sử dụng requests với headers để tránh bị chặn 403.
    """
    try:
        headers = {
            'User-Agent': config.USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'vi,en;q=0.9,en-US;q=0.8',
            'Referer': 'https://www.google.com/',
            'Cache-Control': 'max-age=0',
        }
        
        # 1. Tải HTML bằng requests (tốt hơn newspaper.download trong việc giả lập browser)
        response = requests.get(url, headers=headers, timeout=config.SCRAPE_TIMEOUT)
        response.raise_for_status()
        html = response.text
        
        # 2. Dùng newspaper để parse HTML
        article = Article(url)
        article.set_html(html)
        article.parse()
        
        content = article.text
        if not content or len(content) < config.MIN_ARTICLE_LENGTH:
            return (url, None, f"Content too short ({len(content) if content else 0} chars)")
            
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
            
            # GIỚI HẠN TRONG TEST MODE
            if config.TEST_MODE:
                if config.TEST_RANDOM:
                    print(f"🛠️ [TEST MODE] Lấy ngẫu nhiên {config.TEST_LIMIT} bài để cào nội dung.")
                    random.shuffle(rows)
                else:
                    print(f"🛠️ [TEST MODE] Lấy {config.TEST_LIMIT} bài mới nhất để cào nội dung.")
                rows = rows[:config.TEST_LIMIT]
            
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