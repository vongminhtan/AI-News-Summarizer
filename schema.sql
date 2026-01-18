-- Enable extension for UUID if needed (optional)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table: articles
-- Lưu trữ thông tin bài báo và trạng thái xử lý
CREATE TABLE IF NOT EXISTS articles (
    url TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    source TEXT,
    published_date TIMESTAMP,
    image_url TEXT,
    language VARCHAR(10) DEFAULT 'vi',
    importance_score INT DEFAULT 5,
    origin VARCHAR(10) DEFAULT 'VN',
    
    -- Status Definitions:
    -- 'fetched': Vừa lấy về từ RSS
    -- 'filtered_in': Đã qua bộ lọc (đủ điểm)
    -- 'filtered_out': Bị loại (điểm thấp)
    -- 'scraped': Đã lấy nội dung chi tiết
    -- 'analyzed': Đã phân tích xong
    status VARCHAR(50) DEFAULT 'fetched',
    
    -- Scraped Content
    content TEXT,
    scraped_at TIMESTAMP,

    -- Analysis Data (JSONB mapped from Pydantic ArticleAnalysis)
    summary TEXT,
    tags JSONB, -- Stores {source, sectors, sentiment...}
    author_intent TEXT,
    impact_analysis TEXT,
    analyzed_at TIMESTAMP,
    model_version VARCHAR(50),

    -- Filtering Meta
    filter_score INT,
    filter_reason TEXT,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Table: daily_insights
-- Lưu trữ báo cáo tổng hợp theo ngày
CREATE TABLE IF NOT EXISTS daily_insights (
    date DATE PRIMARY KEY,
    main_trends JSONB, -- List[str]
    hidden_insights JSONB,
    media_steering_analysis TEXT,
    hot_topics JSONB,
    market_sentiment_overlay TEXT,
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- Index cho việc query hiệu quả
CREATE INDEX IF NOT EXISTS idx_articles_status ON articles(status);
CREATE INDEX IF NOT EXISTS idx_articles_created_at ON articles(created_at);
-- Index JSONB để query tags nhanh hơn (VD: tìm bài có sentiment='Tiêu cực')
CREATE INDEX IF NOT EXISTS idx_articles_tags ON articles USING GIN (tags);
