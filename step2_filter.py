import json
import os
import config
import random
from gemini_helper import call_gemini_cli

def filter_news(input_file):
    # --- LOGIC CHO CHẾ ĐỘ TEST ---
    if config.TEST_MODE:
        mode_desc = "ngẫu nhiên" if config.TEST_RANDOM else "mới nhất"
        print(f"🛠️ [TEST MODE] Bỏ qua AI, lấy luôn 3 bài {mode_desc} từ Master Database.")
        
        if os.path.exists(config.STEP1_FILE):
            with open(config.STEP1_FILE, "r", encoding="utf-8") as f:
                try:
                    master_data = json.load(f)
                    if not master_data:
                        return []
                    
                    if config.TEST_RANDOM:
                        # Lấy 3 bài ngẫu nhiên
                        count = min(3, len(master_data))
                        selected_items = random.sample(master_data, count)
                    else:
                        # Lấy 3 bài cuối cùng
                        selected_items = master_data[-3:] if len(master_data) >= 3 else master_data
                        
                    return [item['link'] for item in selected_items]
                except:
                    pass
        print("⚠️ Master Database trống, không có bài để lấy.")
        return []

    # 1. Đọc dữ liệu từ Node 1 (data_new.json)
    if not os.path.exists(input_file):
        print(f"❌ Không tìm thấy file {input_file}")
        return []

    with open(input_file, "r", encoding="utf-8") as f:
        raw_news = json.load(f)
    
    if not raw_news:
        print("⚠️ Không có tin mới để lọc.")
        return []

    # 2. Skip filter nếu số lượng quá ít (tự động giữ lại bài khi không có gì để lọc)
    if len(raw_news) <= 2:
        print(f"ℹ️ Chỉ có {len(raw_news)} tin mới, giữ lại toàn bộ bài.")
        return [item['link'] for item in raw_news]

    # 3. Chuẩn bị danh sách cho AI
    simplified_list = []
    for index, item in enumerate(raw_news):
        simplified_list.append(f"ID: {index} | Title: {item['title']}")
    
    prompt_text = "\n".join(simplified_list)

    query = f"""
    Bạn là một chuyên gia phân tích tài chính. 
    Nhiệm vụ: Đọc danh sách tiêu đề bên dưới và đánh giá tầm ảnh hưởng của chúng đến thị trường tài chính (Việt Nam hoặc Thế giới).

    Yêu cầu Output: 
    - Trả về 1 JSON Array chứa các ID (số nguyên) của những bài báo thỏa mãn:
        1. Điểm đánh giá mức độ quan trọng (Impact Score) >= {config.IMPORTANCE_THRESHOLD}/10. 
        2. Các tiêu chí quan trọng: Ảnh hưởng giá tài sản, chính sách vĩ mô, hoặc báo cáo tài chính lớn.
    - Không giới hạn số lượng bài chọn, miễn là đạt trên {config.IMPORTANCE_THRESHOLD} điểm.
    - Định dạng: [1, 5, 8] (Chỉ trả về JSON, không giải thích).

    Danh sách:
    {prompt_text}
    """

    print(f"--- Đang lọc tin (Threshold: {config.IMPORTANCE_THRESHOLD}) ---")
    response_text = call_gemini_cli(query, model=config.FILTER_MODEL)
    
    if not response_text:
        return []

    # 4. Parse kết quả
    try:
        cleaned_text = response_text.replace("```json", "").replace("```", "").strip()
        selected_ids = json.loads(cleaned_text)
        
        final_links = []
        print(f"\nGemini đã chọn ({len(selected_ids)} bài):")
        for i in selected_ids:
            try:
                item = raw_news[int(i)]
                print(f"- [Score >= {config.IMPORTANCE_THRESHOLD}] {item['title']}")
                final_links.append(item['link'])
            except (IndexError, ValueError):
                continue
            
        return final_links

    except Exception as e:
        print(f"❌ Lỗi khi parse JSON từ AI: {e}")
        return []

# Test Block
if __name__ == "__main__":
    # Test với file data_new.json
    selected_links = filter_news(config.NEW_ONLY_FILE)
    if selected_links:
        with open(config.STEP2_FILE, "w", encoding="utf-8") as f:
            json.dump(selected_links, f, ensure_ascii=False, indent=2)
        print(f"\n✅ Node 2 Hoàn tất! Lưu tại {config.STEP2_FILE}")
    else:
        print("\n❌ Node 2 không chọn bài nào hoặc gặp lỗi.")