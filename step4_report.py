import concurrent.futures
import json
from datetime import datetime, date
import config
from gemini_helper import call_gemini_cli
from models import ArticleAnalysis, ArticleTags, DailyInsight
from database_manager import get_db

def analyze_single_article(article_row):
    """
    Phân tích 1 bài báo.
    Input: article_row (tuple): (url, title, content, published_date)
    Output: ArticleAnalysis object
    """
    url, title, content, published_date = article_row
    
    # Cắt ngắn nội dung nếu quá dài
    content_snippet = content[:config.MAX_CHARS_PER_ARTICLE]
    
    prompt = f"""
    Phân tích bài báo tài chính sau và trích xuất thông tin dưới dạng JSON.
    
    Bài báo: {title}
    Nội dung: {content_snippet}
    
    Yêu cầu Output JSON đúng định dạng sau (không markdown):
    {{
        "summary": "Tóm tắt 3 câu, tập trung vào số liệu và sự kiện",
        "language": "vi hoặc en",
        "importance_score": 1-10,
        "origin": "VN hoặc Global",
        "tags": {{
            "source": "Nguồn báo",
            "sectors": ["Bất động sản", "Ngân hàng", ...],
            "entities": ["Vingroup", "Techcombank", ...],
            "people": ["Phạm Nhật Vượng", ...],
            "locations": ["TP.HCM", "Hà Nội"],
            "keywords": ["FED", "Lãi suất", ...],
            "sentiment": "Tích cực/Tiêu cực/Trung lập"
        }},
        "author_intent": "Mục đích bài viết (PR, Tin tức, Cảnh báo, ...)",
        "impact_analysis": "Dự đoán tác động ngắn hạn (Tăng/Giảm/Ổn định) đến thị trường liên quan."
    }}
    """
    
    try:
        response = call_gemini_cli(prompt, model=config.GEMINI_MODEL)
        cleaned = response.replace("```json", "").replace("```", "").strip()
        data = json.loads(cleaned)
        
        # Validate & Map to Pydantic Model
        analysis = ArticleAnalysis(
            url=url,
            title=title,
            summary=data.get("summary", ""),
            language=data.get("language", "vi"),
            importance_score=data.get("importance_score", 5),
            origin=data.get("origin", "VN"),
            tags=ArticleTags(**data.get("tags", {})),
            author_intent=data.get("author_intent"),
            impact_analysis=data.get("impact_analysis"),
            analyzed_at=datetime.now(),
            model_version=config.GEMINI_MODEL
        )
        return analysis
        
    except Exception as e:
        print(f"❌ Error analyzing {url}: {e}")
        return None

def generate_daily_insights(analyzed_articles):
    """
    Tổng hợp insight từ danh sách các bài báo đã phân tích trong ngày.
    """
    if not analyzed_articles:
        return None

    # Gom nội dung để gửi cho AI tổng hợp
    articles_text = ""
    for idx, art in enumerate(analyzed_articles):
        articles_text += f"[{idx+1}] {art.title} (Sentiment: {art.tags.sentiment})\n"
        articles_text += f"   Summary: {art.summary}\n"
        articles_text += f"   Impact: {art.impact_analysis}\n\n"

    prompt = f"""
    Dựa trên {len(analyzed_articles)} bài báo tài chính sau đây, hãy tổng hợp thành Báo Cáo Chiến Lược Ngày.
    
    Danh sách bài báo:
    {articles_text}
    
    Yêu cầu Output JSON (không markdown):
    {{
        "date": "{date.today()}",
        "main_trends": ["Xu hướng chính 1", "Xu hướng chính 2"],
        "hidden_insights": ["Insight không hiển nhiên mà bạn nhận ra từ dữ liệu trên"],
        "media_steering_analysis": "Phân tích xem truyền thông đang muốn lái dư luận theo hướng nào (FUD, FOMO, hay Thận trọng).",
        "hot_topics": ["Chủ đề 1", "Chủ đề 2"],
        "market_sentiment_overlay": "Nhận định chung về tâm lý thị trường (Bullish/Bearish/Neutral) và lý do."
    }}
    """
    
    try:
        response = call_gemini_cli(prompt, model=config.GEMINI_MODEL)
        cleaned = response.replace("```json", "").replace("```", "").strip()
        data = json.loads(cleaned)
        
        return DailyInsight(**data)
    except Exception as e:
        print(f"❌ Error generating insights: {e}")
        return None

def generate_report():
    print("\n--- [Step 4] Analyzing & Reporting ---")
    
    processed_analyses = []
    
    with get_db() as conn:
        with conn.cursor() as cur:
            # 1. Get articles available for analysis
            cur.execute("SELECT url, title, content, published_date FROM articles WHERE status = 'scraped'")
            rows = cur.fetchall() # [(url, title, content, date), ...]
            
            if not rows:
                print("⚠️ Không có bài báo nào cần phân tích (status='scraped').")
                return

            print(f"🔍 Bắt đầu phân tích {len(rows)} bài báo (Parallel)...")
            
            # 2. Analyze Parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                results = list(executor.map(analyze_single_article, rows))
            
            # 3. Save Analysis Results to DB
            count_success = 0
            for res in results:
                if res:
                    processed_analyses.append(res)
                    try:
                        cur.execute("""
                            UPDATE articles
                            SET summary = %s, tags = %s::jsonb, author_intent = %s, 
                                impact_analysis = %s, analyzed_at = %s, model_version = %s, 
                                language = %s, importance_score = %s, origin = %s, 
                                status = 'analyzed'
                            WHERE url = %s
                        """, (
                            res.summary,
                            res.tags.model_dump_json(), # Pydantic to JSON string
                            res.author_intent,
                            res.impact_analysis,
                            res.analyzed_at,
                            res.model_version,
                            res.language,
                            res.importance_score,
                            res.origin,
                            res.url
                        ))
                        count_success += 1
                    except Exception as e:
                        print(f"❌ DB Error saving analysis for {res.url}: {e}")
            
            conn.commit()
            print(f"✅ Đã phân tích và lưu {count_success} bài.")

            # 4. Generate Daily Insights (from ALL articles analyzed in last 24h)
            
            if processed_analyses:
                print("🧠 Đang tổng hợp Insight thị trường...")
                daily_insight = generate_daily_insights(processed_analyses)
                
                if daily_insight:
                    # Save Insight to DB
                    try:
                        cur.execute("""
                            INSERT INTO daily_insights (date, main_trends, hidden_insights, media_steering_analysis, hot_topics, market_sentiment_overlay, created_at)
                            VALUES (%s, %s::jsonb, %s::jsonb, %s, %s::jsonb, %s, NOW())
                            ON CONFLICT (date) DO UPDATE SET
                                main_trends = EXCLUDED.main_trends,
                                hidden_insights = EXCLUDED.hidden_insights,
                                media_steering_analysis = EXCLUDED.media_steering_analysis,
                                hot_topics = EXCLUDED.hot_topics,
                                market_sentiment_overlay = EXCLUDED.market_sentiment_overlay,
                                created_at = NOW();
                        """, (
                            daily_insight.date,
                            json.dumps(daily_insight.main_trends, ensure_ascii=False),
                            json.dumps(daily_insight.hidden_insights, ensure_ascii=False),
                            daily_insight.media_steering_analysis,
                            json.dumps(daily_insight.hot_topics, ensure_ascii=False),
                            daily_insight.market_sentiment_overlay
                        ))
                        conn.commit()
                        print("✅ Đã lưu Daily Insight vào Database.")
                        
                        # Generate Markdown Report
                        report_file = f"daily_report_{daily_insight.date}.md"
                        with open(report_file, "w", encoding="utf-8") as f:
                            f.write(f"# 📊 Báo Cáo Thị Trường Ngày {daily_insight.date}\n\n")
                            f.write(f"### 🌡️ Tâm Lý Thị Trường: {daily_insight.market_sentiment_overlay}\n\n")
                            f.write("## 🔥 Hot Topics\n")
                            for topic in daily_insight.hot_topics:
                                f.write(f"- {topic}\n")
                            f.write("\n## 👁️ Hidden Insights\n")
                            for insight in daily_insight.hidden_insights:
                                f.write(f"- {insight}\n")
                            f.write("\n## 🧭 Phân Tích Điều Hướng Truyền Thông\n")
                            f.write(f"{daily_insight.media_steering_analysis}\n")
                        print(f"📄 Đã xuất báo cáo Markdown: {report_file}")
                        
                    except Exception as e:
                        print(f"❌ DB Error saving insight: {e}")

if __name__ == "__main__":
    generate_report()