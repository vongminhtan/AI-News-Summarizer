import json
import os
import time
import config
from newspaper import Article, Config

def scrape_content(input_file):
    if not os.path.exists(input_file):
        print(f"❌ Không tìm thấy file {input_file}")
        return []

    with open(input_file, "r", encoding="utf-8") as f:
        links = json.load(f)

    scraped_data = []
    
    # Cấu hình từ file config
    art_config = Config()
    art_config.browser_user_agent = config.USER_AGENT
    art_config.request_timeout = config.SCRAPE_TIMEOUT

    print(f"--- Bắt đầu cào {len(links)} bài báo ---")

    for url in links:
        try:
            print(f"🔄 Đang tải: {url} ...")
            article = Article(url, config=art_config)
            article.download()
            article.parse()
            
            text_content = article.text
            
            if len(text_content) < config.MIN_ARTICLE_LENGTH:
                print(f"⚠️ Cảnh báo: Nội dung quá ngắn. Bỏ qua.")
                continue

            scraped_data.append({
                "url": url,
                "title": article.title,
                "text": text_content,
                "publish_date": str(article.publish_date)
            })
            print(f"✅ Đã lấy xong: {article.title} ({len(text_content)} ký tự)")
            
            time.sleep(config.SCRAPE_SLEEP) 

        except Exception as e:
            print(f"❌ Lỗi khi cào link {url}: {e}")

    return scraped_data

# Test Block
if __name__ == "__main__":
    results = scrape_content(config.STEP2_FILE)
    
    if results:
        with open(config.STEP3_FILE, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n✅ Node 3 Thành công! Lưu tại {config.STEP3_FILE}")
    else:
        print("\n❌ Không lấy được bài nào hoặc file input rỗng.")