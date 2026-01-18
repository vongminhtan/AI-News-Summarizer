import json
import config
import random
from ai_helper import call_ai_cli
from database_manager import get_db

def filter_news():
    print(f"\n--- [Step 2] Filtering News (Threshold: {config.IMPORTANCE_THRESHOLD}) ---")
    
    with get_db() as conn:
        with conn.cursor() as cur:
            # 1. Lấy danh sách bài có status = 'fetched' TRONG VÒNG 24H QUA
            cur.execute("""
                SELECT url, title 
                FROM articles 
                WHERE status = 'fetched' 
                AND published_date >= (NOW() AT TIME ZONE 'UTC') - INTERVAL '24 hours'
            """)
            raw_news = cur.fetchall() # [(url, title), ...]
            
            if not raw_news:
                print("⚠️ Không có bài báo nào cần lọc (status='fetched').")
                return []

            # TEST MODE Logic
            if config.TEST_MODE:
                mode_desc = "ngẫu nhiên" if config.TEST_RANDOM else "mới nhất"
                print(f"🛠️ [TEST MODE] Giới hạn {config.TEST_LIMIT * 2} bài {mode_desc} để gửi AI lọc.")
                
                if config.TEST_RANDOM:
                    random.shuffle(raw_news)
                
                raw_news = raw_news[:config.TEST_LIMIT * 2]

            # 2. Prepare & Run AI Filtering in Batches
            articles_map = {i: (url, title) for i, (url, title) in enumerate(raw_news)}
            all_ids = list(articles_map.keys())
            batch_size = 50 # Xử lý 50 bài mỗi đợt để đảm bảo độ chính xác
            selected_urls = []
            
            print(f"🔍 Bắt đầu đánh giá {len(all_ids)} bài báo (Batch size: {batch_size})...")

            for i in range(0, len(all_ids), batch_size):
                batch_ids = all_ids[i:i + batch_size]
                prompt_list = [f"ID: {bid} | Title: {articles_map[bid][1]}" for bid in batch_ids]
                prompt_text = "\n".join(prompt_list)

                query = f"""
                Bạn là một chuyên gia phân tích tài chính. Hãy đánh giá tầm quan trọng của các tin tức sau (điểm từ 0-10).
                Hệ thống chỉ lấy những tin >= {config.IMPORTANCE_THRESHOLD}.
                
                Yêu cầu Output JSON Array duy nhất, mỗi phần tử chứa:
                - id: ID của bài báo (số nguyên)
                - score: Điểm quan trọng (0-10)
                - reason: Lý do ngắn gọn (1 câu tiếng Việt)

                Ví dụ: [{{"id": 0, "score": 8, "reason": "Ảnh hưởng tỷ giá"}}, {{"id": 1, "score": 2, "reason": "Tin PR"}}]

                Danh sách bài báo:
                {prompt_text}
                """

                print(f"--- Processing batch {i//batch_size + 1}/{(len(all_ids)-1)//batch_size + 1} ---")
                response_text = call_ai_cli(query, model=config.FILTER_MODEL)
                if not response_text:
                    continue

                try:
                    cleaned_text = response_text.replace("```json", "").replace("```", "").strip()
                    ai_results = json.loads(cleaned_text)
                    
                    for res in ai_results:
                        idx = res.get('id')
                        score = res.get('score', 0)
                        reason = res.get('reason', '')
                        
                        if idx in articles_map:
                            url, title = articles_map[idx]
                            
                            if score >= config.IMPORTANCE_THRESHOLD:
                                status = 'filtered_in'
                                selected_urls.append(url)
                                print(f"  ✅ [{score}] {title}")
                            else:
                                status = 'filtered_out'
                            
                            cur.execute("""
                                UPDATE articles 
                                SET status = %s, filter_score = %s, filter_reason = %s 
                                WHERE url = %s
                            """, (status, score, reason, url))
                    
                    conn.commit() # Lưu sau mỗi batch
                except Exception as e:
                    print(f"  ❌ Lỗi xử lý batch: {e}")
            
            return selected_urls

if __name__ == "__main__":
    filter_news()