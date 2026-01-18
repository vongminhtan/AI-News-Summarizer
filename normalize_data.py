import json
import os
import config
from models import ArticleAnalysis, ArticleTags, DailyInsight, SentimentEnum
from datetime import datetime

def load_json(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except:
                return {}
    return {}

def save_json(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def normalize_analysis_db():
    print("🔄 Đang chuẩn hóa Analysis DB...")
    raw_data = load_json(config.ANALYSIS_DB_FILE)
    normalized_data = {}
    
    for url, item in raw_data.items():
        try:
            # Xử lý tags cũ (nếu thiếu field hoặc sai định dạng)
            raw_tags = item.get("tags", {})
            
            # Map sentiment string sang Enum
            sentiment_str = raw_tags.get("sentiment", "Không xác định")
            sentiment_enum = SentimentEnum.UNKNOWN
            for s in SentimentEnum:
                if s.value == sentiment_str:
                    sentiment_enum = s
                    break
            
            tags = ArticleTags(
                source=raw_tags.get("source", "Không xác định"),
                sectors=raw_tags.get("sectors", []),
                entities=raw_tags.get("entities", []),
                people=raw_tags.get("people", []),
                locations=raw_tags.get("locations", []),
                keywords=raw_tags.get("keywords", []),
                sentiment=sentiment_enum
            )

            # Tạo model ArticleAnalysis
            # Nếu item cũ chưa có analyzed_at, gán thời gian hiện tại hoặc một giá trị mặc định
            analyzed_at_str = item.get("analyzed_at")
            if not analyzed_at_str:
                analyzed_at = datetime.now()
            else:
                try:
                    analyzed_at = datetime.fromisoformat(analyzed_at_str)
                except:
                    analyzed_at = datetime.now()

            analysis = ArticleAnalysis(
                url=url, # URL từ key của dict cũ
                title=item.get("title", ""),
                summary=item.get("summary", ""),
                tags=tags,
                author_intent=item.get("author_intent"),
                impact_analysis=item.get("impact_analysis"),
                analyzed_at=analyzed_at,
                model_version=item.get("model_version", config.GEMINI_MODEL)
            )
            
            # Convert model back to dict (mode='json' giúp handle datetime)
            normalized_data[url] = json.loads(analysis.model_dump_json())
            
        except Exception as e:
            print(f"⚠️ Lỗi khi chuẩn hóa bài {url}: {e}")
            continue

    save_json(config.ANALYSIS_DB_FILE, normalized_data)
    print(f"✅ Đã chuẩn hóa {len(normalized_data)} bài phân tích.")

def normalize_daily_insights():
    print("🔄 Đang chuẩn hóa Daily Insights...")
    raw_data = load_json(config.DAILY_INSIGHTS_FILE)
    normalized_data = {}

    for date_str, item in raw_data.items():
        try:
            insight = DailyInsight(
                date=datetime.strptime(date_str, "%Y-%m-%d").date(),
                main_trends=item.get("main_trends", []),
                hidden_insights=item.get("hidden_insights", []),
                media_steering_analysis=item.get("media_steering_analysis"),
                hot_topics=item.get("hot_topics", []),
                market_sentiment_overlay=item.get("market_sentiment_overlay"),
                created_at=datetime.now() # Data cũ chưa có field này
            )
            
            # Key vẫn giữ là string date YYYY-MM-DD
            normalized_data[date_str] = json.loads(insight.model_dump_json())
        
        except Exception as e:
            print(f"⚠️ Lỗi khi chuẩn hóa insight ngày {date_str}: {e}")
            continue

    save_json(config.DAILY_INSIGHTS_FILE, normalized_data)
    print(f"✅ Đã chuẩn hóa {len(normalized_data)} insight ngày.")

if __name__ == "__main__":
    normalize_analysis_db()
    normalize_daily_insights()
