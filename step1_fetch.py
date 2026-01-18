import feedparser
import json
import os
import config

def load_master_data():
    """Load toàn bộ dữ liệu từ Master Database."""
    if os.path.exists(config.STEP1_FILE):
        with open(config.STEP1_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except:
                return []
    return []

def save_data(file_path, data):
    """Ghi dữ liệu ra file json."""
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def fetch_rss():
    master_data = load_master_data()
    existing_links = {item['link'] for item in master_data}
    
    all_batch_items = []    # Tất cả tin lấy được trong lần này
    new_only_items = []     # Chỉ các tin mới hoàn toàn
    
    print(f"--- Đang quét {len(config.RSS_URLS)} nguồn RSS ---")
    if config.TEST_MODE:
        print(f"Chế độ TEST: Giới hạn {config.TEST_LIMIT} bài mỗi nguồn.")

    for url in config.RSS_URLS:
        feed = feedparser.parse(url)
        count_per_source = 0
        
        for entry in feed.entries:
            if config.TEST_MODE and count_per_source >= config.TEST_LIMIT:
                break
                
            item = {
                "title": entry.title,
                "link": entry.link,
                "published": entry.get("published", "N/A")
            }
            
            all_batch_items.append(item)
            
            # Kiểm tra xem có phải tin mới không
            if item['link'] not in existing_links:
                new_only_items.append(item)
                master_data.append(item)
                existing_links.add(item['link'])
            
            count_per_source += 1
            
        print(f"[{url}] Lấy được {count_per_source} bài.")

    # 1. Cập nhật Master Database (Chỉ thêm mới)
    if new_only_items:
        save_data(config.STEP1_FILE, master_data)
        print(f"✅ Đã cập nhật Master Database: +{len(new_only_items)} bài (Tổng: {len(master_data)})")
    else:
        print("ℹ️ Không có bài báo nào mới so với Master Database.")

    # 2. Lưu Batch File (Tất cả tin vừa lấy - ghi đè)
    save_data(config.BATCH_FILE, all_batch_items)
    
    # 3. Lưu New Only File (Chỉ các tin mới - ghi đè)
    save_data(config.NEW_ONLY_FILE, new_only_items)

    return all_batch_items, new_only_items

# Test Block
if __name__ == "__main__":
    batch, new = fetch_rss()
    print(f"\n✅ Node 1 Hoàn tất!")
    print(f"- Batch file (tất cả): {len(batch)} bài -> {config.BATCH_FILE}")
    print(f"- New file (chỉ tin mới): {len(new)} bài -> {config.NEW_ONLY_FILE}")
    print(f"- Master database (tổng hợp): {config.STEP1_FILE}")