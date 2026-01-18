import json
import os
import datetime
import concurrent.futures
import config
from gemini_helper import call_gemini_cli
from models import ArticleAnalysis, ArticleTags, DailyInsight

def load_db(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except:
                return {}
    return {}

def save_db(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def analyze_single_article(article):
    url = article['url']
    title = article['title']
    content = article['text']
    
    analysis_db = load_db(config.ANALYSIS_DB_FILE)
    if url in analysis_db:
        print(f"⏩ Đã có phân tích cho bài: {title}. Skip.")
        return analysis_db[url]

    print(f"🧠 Đang phân tích chuyên sâu: {title}")
    
    prompt = f"""
    Bạn là một chuyên gia phân tích dữ liệu và truyền thông tài chính.
    Hãy phân tích bài báo sau đây và trả về kết quả dưới dạng JSON duy nhất, tuân thủ đúng định dạng yêu cầu.

    Nội dung bài báo:
    Tiêu đề: {title}
    Nội dung: {content[:config.MAX_CHARS_PER_ARTICLE]}

    Yêu cầu JSON Output:
    {{
        "url": "{url}",
        "title": "{title}",
        "summary": "Tóm tắt ngắn gọn 1-2 câu",
        "tags": {{
            "source": "Tên báo/nguồn tin",
            "sectors": ["Ngành nghề"],
            "entities": ["Tên công ty"],
            "people": ["Tên người"],
            "locations": ["Địa danh"],
            "keywords": ["Từ khóa"],
            "sentiment": "Tích cực | Tiêu cực | Trung lập | Không xác định"
        }},
        "author_intent": "Mục đích bài viết",
        "impact_analysis": "Phân tích tác động"
    }}
    """

    response_text = call_gemini_cli(prompt, model=config.GEMINI_MODEL)
    if not response_text:
        return None

    try:
        cleaned_text = response_text.replace("```json", "").replace("```", "").strip()
        raw_json = json.loads(cleaned_text)
        
        # Validate bằng Pydantic
        # Lưu ý: AI có thể không trả về url/title trong json, ta cần inject vào
        raw_json["url"] = url
        raw_json["title"] = title
        
        analysis_model = ArticleAnalysis(**raw_json)
        
        # Serialize thành dict để lưu JSON
        analysis_dict = json.loads(analysis_model.model_dump_json())
        
        # Lưu vào DB (lưu ý concurrent write)
        analysis_db = load_db(config.ANALYSIS_DB_FILE)
        analysis_db[url] = analysis_dict
        save_db(config.ANALYSIS_DB_FILE, analysis_db)
        
        return analysis_dict
    except Exception as e:
        print(f"❌ Lỗi validation/parse bài '{title}': {e}")
        return None

def process_articles_parallel(articles):
    print(f"\n--- Bắt đầu phân tích song song {len(articles)} bài báo ---")
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        future_to_article = {executor.submit(analyze_single_article, art): art for art in articles}
        for future in concurrent.futures.as_completed(future_to_article):
            res = future.result()
            if res:
                results.append(res)
    return results

def generate_daily_insight():
    print(f"📊 Đang tổng hợp Insight 24h qua...")
    
    analysis_db = load_db(config.ANALYSIS_DB_FILE)
    now = datetime.datetime.now()
    yesterday = now - datetime.timedelta(hours=24)
    
    recent_analyses = []
    for url, data in analysis_db.items():
        try:
            analyzed_at = datetime.datetime.fromisoformat(data['analyzed_at'])
            if analyzed_at > yesterday:
                recent_analyses.append(data)
        except:
            continue
            
    if not recent_analyses:
        print("⚠️ Không có dữ liệu phân tích trong 24h qua để tạo insight.")
        return

    context = ""
    for idx, data in enumerate(recent_analyses, 1):
        # Data đã được normalized, truy xuất an toàn
        tags = data.get('tags', {})
        context += f"Bài {idx}: {data['title']}. Tóm tắt: {data['summary']}. Tags: {tags}\n"

    prompt = f"""
    Dựa trên các phân tích bài báo trong 24h qua sau đây:
    {context}

    Hãy thực hiện phân tích tổng quát (Insight Report).
    Trả về kết quả JSON với các trường:
    {{
        "date": "{now.strftime('%Y-%m-%d')}",
        "main_trends": ["Chanel 1", "Chanel 2"],
        "hidden_insights": ["Insight 1"],
        "media_steering_analysis": "Text analysis...",
        "hot_topics": ["Topic 1"],
        "market_sentiment_overlay": "Text..."
    }}
    """

    response_text = call_gemini_cli(prompt, model=config.GEMINI_MODEL)
    if not response_text:
        return

    try:
        cleaned_text = response_text.replace("```json", "").replace("```", "").strip()
        raw_json = json.loads(cleaned_text)
        
        # Validate bằng Pydantic
        insight_model = DailyInsight(**raw_json)
        
        insight_dict = json.loads(insight_model.model_dump_json())
        date_str = str(insight_model.date)
        
        insights_db = load_db(config.DAILY_INSIGHTS_FILE)
        insights_db[date_str] = insight_dict
        save_db(config.DAILY_INSIGHTS_FILE, insights_db)
        
        # Tạo report Markdown
        report_md = f"# DAILY FINANCIAL INSIGHTS - {date_str}\n\n"
        report_md += f"*(Created at: {insight_model.created_at.strftime('%H:%M %d/%m/%Y')})*\n\n"
        report_md += "## 📈 Xu hướng chính\n" + "\n".join([f"- {i}" for i in insight_model.main_trends]) + "\n\n"
        report_md += "## 💡 Hidden Insights\n" + "\n".join([f"- {i}" for i in insight_model.hidden_insights]) + "\n\n"
        report_md += "## 🗣️ Media Steering Analysis\n" + (insight_model.media_steering_analysis or "N/A") + "\n\n"
        report_md += "## 🔥 Hot Topics\n" + ", ".join(insight_model.hot_topics) + "\n"
        
        report_filename = f"daily_report_{date_str}.md"
        with open(report_filename, "w", encoding="utf-8") as f:
            f.write(report_md)
            
        print(f"✅ Đã tạo báo cáo Insight: {report_filename}")
        return insight_dict
    except Exception as e:
        print(f"❌ Lỗi parse Daily Insight: {e}")

def generate_report(input_file):
    # Đọc dữ liệu từ Node 3 (Content đã cào)
    if not os.path.exists(input_file):
        print(f"❌ Không tìm thấy file {input_file}")
        return

    with open(input_file, "r", encoding="utf-8") as f:
        articles = json.load(f)

    if not articles:
        return

    # Bước 1: Phân tích từng bài song song
    process_articles_parallel(articles)
    
    # Bước 2: Tổng hợp Insight 24h
    generate_daily_insight()

if __name__ == "__main__":
    generate_report(config.STEP3_FILE)