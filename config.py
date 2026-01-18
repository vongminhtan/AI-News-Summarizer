import os

# --- Chế độ chạy ---
TEST_MODE = True  # Chuyển thành False khi chạy thật
TEST_LIMIT = 10    # Số lượng bài tối đa lấy từ mỗi nguồn khi ở chế độ TEST
TEST_RANDOM = True # Nếu True, trong mode TEST sẽ chọn bài ngẫu nhiên thay vì bài mới nhất
USE_SSH_TUNNEL = True # TRUE khi chạy ở Local Mac, FALSE khi chạy ở VPS

# --- Cấu hình chung ---
DATA_DIR = "data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# File lưu trữ dữ liệu
STEP1_FILE = os.path.join(DATA_DIR, "data_step1.json") # Tổng hợp toàn bộ dữ liệu từ trước tới nay
BATCH_FILE = os.path.join(DATA_DIR, "data_batch.json") # Tất cả tin lấy được trong lần chạy này (ghi đè)
NEW_ONLY_FILE = os.path.join(DATA_DIR, "data_new.json") # Chỉ các tin mới chưa từng thấy (ghi đè)
STEP2_FILE = os.path.join(DATA_DIR, "data_step2.json")
STEP3_FILE = os.path.join(DATA_DIR, "data_step3.json")
ANALYSIS_DB_FILE = os.path.join(DATA_DIR, "analysis_db.json")   # DB lưu phân tích từng bài báo
DAILY_INSIGHTS_FILE = os.path.join(DATA_DIR, "daily_insights.json") # DB lưu insight theo ngày
HISTORY_FILE = os.path.join(DATA_DIR, "processed_history.json")

# --- RSS URLs ---
RSS_URLS = [
    "https://cafef.vn/tai-chinh-quoc-te.rss",
    "https://vnexpress.net/rss/kinh-doanh.rss"
]

# --- Gemini Config ---
GEMINI_MODEL = "gemini-2.5-pro"
# Có thể dùng model rẻ hơn cho bước lọc tin nếu muốn tiết kiệm
FILTER_MODEL = "gemini-2.5-flash" 
IMPORTANCE_THRESHOLD = 7 # Điểm tối thiểu (1-10) để lấy bài báo

# --- Scraping Config ---
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
SCRAPE_TIMEOUT = 15
SCRAPE_SLEEP = 2
MIN_ARTICLE_LENGTH = 100

# --- Report Config ---
MAX_ARTICLES_PER_REPORT = 5
MAX_CHARS_PER_ARTICLE = 5000
REPORT_TITLE_PREFIX = "Báo Cáo Điểm Tin Tài Chính"
