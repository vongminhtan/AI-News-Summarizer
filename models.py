from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, date
from enum import Enum
import config

class SentimentEnum(str, Enum):
    POSITIVE = "Tích cực"
    NEGATIVE = "Tiêu cực"
    NEUTRAL = "Trung lập"
    UNKNOWN = "Không xác định"

class ArticleTags(BaseModel):
    source: Optional[str] = Field(default="Không xác định", description="Tên báo hoặc nguồn tin")
    sectors: List[str] = Field(default_factory=list, description="Ngành nghề liên quan")
    entities: List[str] = Field(default_factory=list, description="Tên công ty, tổ chức")
    people: List[str] = Field(default_factory=list, description="Tên các nhân vật xuất hiện")
    locations: List[str] = Field(default_factory=list, description="Địa danh")
    keywords: List[str] = Field(default_factory=list, description="Từ khóa quan trọng")
    sentiment: Optional[SentimentEnum] = Field(default=SentimentEnum.UNKNOWN, description="Cảm xúc của bài báo")

class ArticleAnalysis(BaseModel):
    url: str
    title: str
    summary: str
    tags: ArticleTags
    author_intent: Optional[str] = Field(default=None, description="Mục đích của tác giả")
    impact_analysis: Optional[str] = Field(default=None, description="Tác động dự kiến")
    analyzed_at: datetime = Field(default_factory=datetime.now)
    model_version: str = Field(default=config.GEMINI_MODEL, description="Model AI sử dụng để phân tích")

class DailyInsight(BaseModel):
    date: date
    main_trends: List[str] = Field(default_factory=list)
    hidden_insights: List[str] = Field(default_factory=list)
    media_steering_analysis: Optional[str] = None
    hot_topics: List[str] = Field(default_factory=list)
    market_sentiment_overlay: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
