import feedparser
import time
import calendar
import re
from datetime import datetime, timedelta, timezone
import config
from database_manager import get_db

def extract_image(entry):
    """Trích xuất link ảnh từ entry của RSS"""
    # 1. Thử lấy từ media_content (NYT sử dụng cái này)
    if 'media_content' in entry:
        for media in entry.media_content:
            if media.get('medium') == 'image' or media.get('type', '').startswith('image/'):
                return media.get('url')

    # 2. Thử lấy từ media_thumbnail (phổ biến ở một số RSS)
    if 'media_thumbnail' in entry and len(entry.media_thumbnail) > 0:
        return entry.media_thumbnail[0].get('url')
    
    # 3. Thử lấy từ enclosures
    if 'enclosures' in entry:
        for enc in entry.enclosures:
            if enc.get('type', '').startswith('image/'):
                return enc.get('url')
    
    # 4. Phổ biến nhất ở VNExpress/Cafef: Link ảnh nằm trong description
    description = entry.get('description', '')
    if description:
        # Tìm tag <img src="...">
        img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', description)
        if img_match:
            return img_match.group(1)
            
    return None

def fetch_rss():
    print(f"--- Đang quét {len(config.RSS_URLS)} nguồn RSS ---")
    if config.TEST_MODE:
        print(f"Chế độ TEST: Giới hạn {config.TEST_LIMIT} bài mỗi nguồn.")

    new_articles_count = 0
    updated_articles_count = 0
    total_articles = 0
    skipped_count = 0
    
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
                        published_parsed = entry.get('published_parsed')
                        if published_parsed:
                            published_date = datetime.fromtimestamp(calendar.timegm(published_parsed), tz=timezone.utc).replace(tzinfo=None)
                        else:
                            published_date = datetime.now(timezone.utc).replace(tzinfo=None)
                        
                        # Chỉ lấy bài trong vòng 24h qua (So sánh ở UTC)
                        if datetime.now(timezone.utc).replace(tzinfo=None) - published_date > timedelta(hours=24):
                            skipped_count += 1
                            continue
                            
                        source = rss_url
                        image_url = extract_image(entry)

                        if not link: continue

                        # Upsert vào DB
                        cur.execute("""
                            INSERT INTO articles (url, title, source, published_date, image_url, status, created_at, updated_at)
                            VALUES (%s, %s, %s, %s, %s, 'fetched', NOW(), NOW())
                            ON CONFLICT (url) DO UPDATE SET
                                title = EXCLUDED.title,
                                image_url = COALESCE(articles.image_url, EXCLUDED.image_url),
                                published_date = COALESCE(articles.published_date, EXCLUDED.published_date),
                                updated_at = NOW()
                            RETURNING (xmax = 0) AS is_inserted;
                        """, (link, title, source, published_date, image_url))
                        
                        result = cur.fetchone()
                        if result:
                            if result[0]: # is_inserted
                                new_articles_count += 1
                            else:
                                updated_articles_count += 1
                            
                    except Exception as e:
                        print(f"⚠️ Lỗi xử lý bài: {e}")
                        continue
            
            conn.commit()

    print(f"✅ Đã cập nhật database: +{new_articles_count} bài mới, {updated_articles_count} bài cũ được cập nhật (Tổng quét: {total_articles}, Bỏ qua: {skipped_count} bài quá 24h)")
    
    return total_articles, new_articles_count

if __name__ == "__main__":
    fetch_rss()