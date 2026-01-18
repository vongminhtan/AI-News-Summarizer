import sys
import os
import json
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from database_manager import get_db
from models import ArticleAnalysis, DailyInsight

def load_json(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except:
                return {}
    return {} or []

def migrate_articles():
    print("\n--- Migrating Articles ---")
    # 1. Load Step 1 Data (Fetched)
    fetched_data = load_json(config.STEP1_FILE) # [dict, dict...]
    
    # 2. Load Analysis Data (Analyzed)
    analysis_data = load_json(config.ANALYSIS_DB_FILE) # {url: dict}
    
    count_fetched = 0
    count_analyzed = 0

    with get_db() as conn:
        with conn.cursor() as cur:
            # A. Migrate Fetched Articles (Basic Info)
            for item in fetched_data:
                url = item.get('link') or item.get('url')
                if not url: continue
                
                # Check exist
                cur.execute("SELECT url FROM articles WHERE url = %s", (url,))
                if cur.fetchone():
                    continue

                cur.execute("""
                    INSERT INTO articles (url, title, source, published_date, status, created_at)
                    VALUES (%s, %s, %s, %s, 'fetched', NOW())
                    ON CONFLICT (url) DO NOTHING;
                """, (
                    url,
                    item.get('title', ''),
                    item.get('source', ''),
                    item.get('published_date'), # Might need parsing if string
                ))
                count_fetched += 1
            
            # B. Migrate Analyzed Data (Update records)
            for url, data in analysis_data.items():
                # Validate with Pydantic first
                try:
                    # Chuyển tags (ArticleTags object) sang dict để lưu JSONB
                    tags_dict = data.get('tags', {})
                    
                    # Convert to JSON string for SQL
                    tags_json = json.dumps(tags_dict, ensure_ascii=False)
                    
                    cur.execute("""
                        INSERT INTO articles (url, title, summary, tags, author_intent, impact_analysis, analyzed_at, model_version, status, content, scraped_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'analyzed', 'From JSON Migration', NOW())
                        ON CONFLICT (url) DO UPDATE SET
                            summary = EXCLUDED.summary,
                            tags = EXCLUDED.tags,
                            author_intent = EXCLUDED.author_intent,
                            impact_analysis = EXCLUDED.impact_analysis,
                            analyzed_at = EXCLUDED.analyzed_at,
                            model_version = EXCLUDED.model_version,
                            status = 'analyzed';
                    """, (
                        url,
                        data.get('title', ''),
                        data.get('summary', ''),
                        tags_json, 
                        data.get('author_intent'),
                        data.get('impact_analysis'),
                        data.get('analyzed_at'),
                        data.get('model_version'),
                    ))
                    count_analyzed += 1
                except Exception as e:
                    print(f"⚠️ Skip article {url}: {e}")
                    
            conn.commit()
    
    print(f"✅ Imported {count_fetched} fetched articles.")
    print(f"✅ Updated {count_analyzed} analyzed articles.")

def migrate_insights():
    print("\n--- Migrating Daily Insights ---")
    insights_data = load_json(config.DAILY_INSIGHTS_FILE) # {date_str: dict}
    
    count = 0
    with get_db() as conn:
        with conn.cursor() as cur:
            for date_str, data in insights_data.items():
                try:
                    cur.execute("""
                        INSERT INTO daily_insights (date, main_trends, hidden_insights, media_steering_analysis, hot_topics, market_sentiment_overlay, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (date) DO NOTHING;
                    """, (
                        data.get('date'),
                        json.dumps(data.get('main_trends', []), ensure_ascii=False),
                        json.dumps(data.get('hidden_insights', []), ensure_ascii=False),
                        data.get('media_steering_analysis'),
                        json.dumps(data.get('hot_topics', []), ensure_ascii=False),
                        data.get('market_sentiment_overlay'),
                        data.get('created_at')
                    ))
                    count += 1
                except Exception as e:
                    print(f"⚠️ Skip insight {date_str}: {e}")
            conn.commit()
            
    print(f"✅ Imported {count} daily insights.")

if __name__ == "__main__":
    migrate_articles()
    migrate_insights()
