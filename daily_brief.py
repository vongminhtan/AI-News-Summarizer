import step1_fetch
import step2_filter
import step3_scrape
import step4_report
import config
import notifier

def main():
    print("🚀 BẮT ĐẦU QUY TRÌNH TỔNG HỢP TIN SÁNG (DB-DRIVEN) 🚀")
    if config.TEST_MODE:
        print("⚠️ ĐANG CHẠY CHẾ ĐỘ TEST")

    # BƯỚC 1: LẤY RSS -> DB
    print("\n[1/4] Fetching RSS...")
    total, new_count = step1_fetch.fetch_rss()
    
    if new_count == 0 and not config.TEST_MODE:
        print("☕ Không có tin nào mới. Nghỉ ngơi thôi!")
        return

    # BƯỚC 2: LỌC TIN (GEMINI) -> UPDATE STATUS 'filtered_in'
    print("\n[2/4] Filtering News...")
    selected_urls = step2_filter.filter_news()
    if not selected_urls:
        print("❌ Không có bài báo nào được chọn sau khi lọc.")
        return

    # BƯỚC 3: CÀO NỘI DUNG -> UPDATE STATUS 'scraped'
    print("\n[3/4] Scraping Content...")
    scraped_urls = step3_scrape.scrape_articles()
    if not scraped_urls:
        print("❌ Không có bài báo nào cào được nội dung.")
        return

    # BƯỚC 4: TỔNG HỢP BÁO CÁO -> UPDATE STATUS 'analyzed' & INSERT INSIGHTS
    print("\n[4/4] Writing Report...")
    daily_insight, analyzed_count = step4_report.generate_report()

    if daily_insight:
        print("\n🔔 Sending Telegram notification...")
        msg = notifier.format_daily_insight_message(daily_insight, analyzed_count)
        notifier.send_telegram_message(msg)

    print("\n🎉 HOÀN THÀNH NHIỆM VỤ!")

if __name__ == "__main__":
    main()