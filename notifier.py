import requests
import config

def send_telegram_message(message: str):
    """
    Gửi tin nhắn Telegram thông qua Bot API.
    """
    if not config.ENABLE_TELEGRAM:
        return

    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        print("⚠️ Telegram Config thiếu Token hoặc Chat ID. Bỏ qua gửi thông báo.")
        return

    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": config.TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            print(f"❌ Lỗi gửi Telegram: {response.text}")
        else:
            print("✅ Đã gửi thông báo Telegram.")
    except Exception as e:
        print(f"❌ Lỗi kết nối Telegram: {e}")

def format_daily_insight_message(insight, analyzed_count):
    """
    Định dạng tin nhắn Telegram từ DailyInsight object.
    """
    msg = f"<b>🚀 AI NEWS DASHBOARD UPDATE</b>\n\n"
    msg += f"📅 Ngày: {insight.date}\n"
    msg += f"📰 Số bài đã phân tích: <b>{analyzed_count}</b>\n"
    msg += f"🌡️ Tâm lý thị trường: <b>{insight.market_sentiment_overlay}</b>\n\n"
    
    msg += f"<b>🔥 Hot Topics:</b>\n"
    for topic in insight.hot_topics[:5]:
        msg += f"• {topic}\n"
    
    msg += f"\n<b>📊 Xu hướng chính:</b>\n"
    for trend in insight.main_trends[:3]:
        msg += f"• {trend}\n"
        
    msg += f"\n<b>👁️ Hidden Insights:</b>\n"
    for hi in insight.hidden_insights[:2]:
        msg += f"• {hi}\n"
        
    msg += f"\n🔗 <a href='https://ai-news.hitluckvocvach.com'>Xem Dashboard chi tiết</a>"
    
    return msg
