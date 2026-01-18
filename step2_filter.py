import json
import config
import random
from gemini_helper import call_gemini_cli
from database_manager import get_db

def filter_news():
    print(f"\n--- [Step 2] Filtering News (Threshold: {config.IMPORTANCE_THRESHOLD}) ---")
    
    with get_db() as conn:
        with conn.cursor() as cur:
            # 1. Lấy danh sách bài có status = 'fetched'
            cur.execute("SELECT url, title FROM articles WHERE status = 'fetched'")
            raw_news = cur.fetchall() # [(url, title), ...]
            
            if not raw_news:
                print("⚠️ Không có bài báo nào cần lọc (status='fetched').")
                return []

            # TEST MODE Logic
            if config.TEST_MODE:
                mode_desc = "ngẫu nhiên" if config.TEST_RANDOM else "mới nhất"
                print(f"🛠️ [TEST MODE] Giới hạn 3 bài {mode_desc} để test.")
                
                if config.TEST_RANDOM:
                    selected_indices = random.sample(range(len(raw_news)), min(3, len(raw_news)))
                else:
                    selected_indices = list(range(min(3, len(raw_news))))
                
                selected_urls = []
                for idx, (url, title) in enumerate(raw_news):
                    if idx in selected_indices:
                        cur.execute("""
                            UPDATE articles 
                            SET status = 'filtered_in', filter_score = 10, filter_reason = 'Selected in TEST MODE' 
                            WHERE url = %s
                        """, (url,))
                        selected_urls.append(url)
                    else:
                        # Mark others as filtered_out even in test mode to clean up
                        cur.execute("""
                            UPDATE articles 
                            SET status = 'filtered_out', filter_score = 0, filter_reason = 'Not selected in TEST MODE' 
                            WHERE url = %s
                        """, (url,))
                
                conn.commit()
                return selected_urls

            # 2. Prepare AI Prompt
            articles_map = {i: (url, title) for i, (url, title) in enumerate(raw_news)}
            prompt_list = [f"ID: {i} | Title: {title}" for i, (url, title) in articles_map.items()]
            prompt_text = "\n".join(prompt_list)

            query = f"""
            Bạn là một chuyên gia phân tích tài chính. Hãy đánh giá tầm quan trọng của các tin tức sau.
            
            Yêu cầu Output JSON Array duy nhất, mỗi phần tử chứa:
            - id: ID của bài báo (số nguyên)
            - score: Điểm quan trọng (0-10)
            - reason: Lý do ngắn gọn (1 câu tiếng Việt)

            Ví dụ: [{"id": 0, "score": 8, "reason": "Ảnh hưởng tỷ giá"}, {"id": 1, "score": 2, "reason": "Tin PR"}]

            Danh sách:
            {prompt_text}
            """

            response_text = call_gemini_cli(query, model=config.FILTER_MODEL)
            if not response_text:
                return []

            try:
                cleaned_text = response_text.replace("```json", "").replace("```", "").strip()
                ai_results = json.loads(cleaned_text) # List of dicts
                
                selected_urls = []
                print(f"\nKết quả đánh giá từ AI:")
                
                for res in ai_results:
                    idx = res.get('id')
                    score = res.get('score', 0)
                    reason = res.get('reason', '')
                    
                    if idx in articles_map:
                        url, title = articles_map[idx]
                        
                        if score >= config.IMPORTANCE_THRESHOLD:
                            status = 'filtered_in'
                            selected_urls.append(url)
                            print(f"✅ [{score}] {title} -> {reason}")
                        else:
                            status = 'filtered_out'
                            print(f"❌ [{score}] {title} -> {reason}")
                        
                        # Cập nhật DB cho từng bài
                        cur.execute("""
                            UPDATE articles 
                            SET status = %s, filter_score = %s, filter_reason = %s 
                            WHERE url = %s
                        """, (status, score, reason, url))
                
                conn.commit()
                return selected_urls

            except Exception as e:
                print(f"❌ Lỗi khi xử lý kết quả AI: {e}")
                return []

if __name__ == "__main__":
    filter_news()