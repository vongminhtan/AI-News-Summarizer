import concurrent.futures
import json
from datetime import datetime, date, timezone
import config
import random
from ai_helper import call_ai_cli
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
        response = call_ai_cli(prompt, model=config.GEMINI_MODEL)
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
        "date": "{datetime.now(timezone.utc).date()}",
        "main_trends": ["Xu hướng chính 1", "Xu hướng chính 2"],
        "hidden_insights": ["Insight không hiển nhiên mà bạn nhận ra từ dữ liệu trên"],
        "media_steering_analysis": "Phân tích xem truyền thông đang muốn lái dư luận theo hướng nào (FUD, FOMO, hay Thận trọng).",
        "hot_topics": ["Chủ đề 1", "Chủ đề 2"],
        "market_sentiment_overlay": "Nhận định chung về tâm lý thị trường (Bullish/Bearish/Neutral) và lý do."
    }}
    """
    
    try:
        response = call_ai_cli(prompt, model=config.GEMINI_MODEL)
        cleaned = response.replace("```json", "").replace("```", "").strip()
        data = json.loads(cleaned)
        
        return DailyInsight(**data)
    except Exception as e:
        print(f"❌ Error generating insights: {e}")
        return None

def generate_report():
    print("\n--- [Step 4] Analyzing & Reporting ---")
    
    all_processed_analyses = []
    
    with get_db() as conn:
        with conn.cursor() as cur:
            # 1. Get articles available for analysis
            cur.execute("""
                SELECT url, title, content, published_date 
                FROM articles 
                WHERE status = 'scraped' 
                AND published_date >= (NOW() AT TIME ZONE 'UTC') - INTERVAL '24 hours'
            """)
            rows = cur.fetchall()
            
            # GIỚI HẠN TRONG TEST MODE
            if config.TEST_MODE:
                if config.TEST_RANDOM:
                    print(f"🛠️ [TEST MODE] Lấy ngẫu nhiên {config.TEST_LIMIT} bài để phân tích.")
                    random.shuffle(rows)
                else:
                    print(f"🛠️ [TEST MODE] Lấy {config.TEST_LIMIT} bài mới nhất để phân tích.")
                rows = rows[:config.TEST_LIMIT]
            
            if not rows:
                print("⚠️ Không có bài báo nào cần phân tích (status='scraped').")
                return None, 0
 
            total_articles = len(rows)
            print(f"🔍 Bắt đầu phân tích {total_articles} bài báo (6 Hybrid workers, update immediately)...")
            
            # 2. Analyze & Save sequentially as tasks complete
            with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
                # Submit all tasks
                future_to_url = {executor.submit(analyze_single_article, row): row[0] for row in rows}
                
                count = 0
                for future in concurrent.futures.as_completed(future_to_url):
                    url = future_to_url[future]
                    count += 1
                    try:
                        res = future.result()
                        if res:
                            all_processed_analyses.append(res)
                            # Update DB immediately for this article
                            cur.execute("""
                                UPDATE articles
                                SET summary = %s, tags = %s::jsonb, author_intent = %s, 
                                    impact_analysis = %s, analyzed_at = %s, model_version = %s, 
                                    language = %s, importance_score = %s, origin = %s, 
                                    status = 'analyzed'
                                WHERE url = %s
                            """, (
                                res.summary,
                                res.tags.model_dump_json(),
                                res.author_intent,
                                res.impact_analysis,
                                res.analyzed_at, # res.analyzed_at is already UTC from get_now_utc()
                                res.model_version,
                                res.language,
                                res.importance_score,
                                res.origin,
                                res.url
                            ))
                            conn.commit() # Commit ngay lập tức
                            print(f"  ✅ [{count}/{total_articles}] Analyzed & Saved: {res.title[:50]}...")
                        else:
                            print(f"  ⚠️ [{count}/{total_articles}] Failed analysis for: {url}")
                            
                    except Exception as e:
                        print(f"  ❌ [{count}/{total_articles}] Unexpected error for {url}: {e}")
            
            print(f"🎉 Hoàn tất phân tích {len(all_processed_analyses)}/{total_articles} bài.")

            # 4. Generate Daily Insights (from ALL articles analyzed in last 24h)
            
            if all_processed_analyses:
                print("🧠 Đang tổng hợp Insight thị trường...")
                daily_insight = generate_daily_insights(all_processed_analyses)
                
                if daily_insight:
                    # Save Insight to DB
                    try:
                        cur.execute("""
                            INSERT INTO daily_insights (date, main_trends, hidden_insights, media_steering_analysis, hot_topics, market_sentiment_overlay, created_at)
                            VALUES (%s, %s::jsonb, %s::jsonb, %s, %s::jsonb, %s, NOW() AT TIME ZONE 'UTC')
                            ON CONFLICT (date) DO UPDATE SET
                                main_trends = EXCLUDED.main_trends,
                                hidden_insights = EXCLUDED.hidden_insights,
                                media_steering_analysis = EXCLUDED.media_steering_analysis,
                                hot_topics = EXCLUDED.hot_topics,
                                market_sentiment_overlay = EXCLUDED.market_sentiment_overlay,
                                created_at = NOW() AT TIME ZONE 'UTC';
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
                        return daily_insight, len(all_processed_analyses)
                        
                    except Exception as e:
                        print(f"❌ DB Error saving insight: {e}")
            
            return None, len(all_processed_analyses)

if __name__ == "__main__":
    generate_report()