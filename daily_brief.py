import step1_fetch
import step2_filter
import step3_scrape
import step4_report
import json
import os
import config

def main():
    print("🚀 BẮT ĐẦU QUY TRÌNH TỔNG HỢP TIN SÁNG 🚀")
    if config.TEST_MODE:
        print(f"⚠️ ĐANG CHẠY CHẾ ĐỘ TEST (Giới hạn {config.TEST_LIMIT} bài mỗi nguồn)")
    
    # BƯỚC 1: LẤY RSS
    print("\n[1/4] Fetching RSS...")
    batch_news, new_news = step1_fetch.fetch_rss()
    
    if not new_news and not config.TEST_MODE:
        print("☕ Không có tin nào mới so với database. Nghỉ ngơi thôi!")
        return

    # LỌC TIN (GEMINI)
    print("\n[2/4] Filtering News...")
    selected_links = step2_filter.filter_news(config.NEW_ONLY_FILE)
    if not selected_links:
        print("🛑 Không có tin nào đủ quan trọng để báo cáo. Dừng.")
        return
    with open(config.STEP2_FILE, "w", encoding="utf-8") as f:
        json.dump(selected_links, f, ensure_ascii=False, indent=2)

    # BƯỚC 3: CÀO NỘI DUNG
    print("\n[3/4] Scraping Content...")
    articles = step3_scrape.scrape_content(config.STEP2_FILE)
    if not articles:
        print("❌ Không lấy được nội dung chi tiết. Dừng.")
        return
    with open(config.STEP3_FILE, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

    # BƯỚC 4: VIẾT BÁO CÁO
    print("\n[4/4] Writing Report...")
    step4_report.generate_report(config.STEP3_FILE)
    
    print("\n🎉 HOÀN THÀNH NHIỆM VỤ!")

if __name__ == "__main__":
    main()