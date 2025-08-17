from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Optional

Base = declarative_base()

class TokenPair(Base):
    """Model for storing Solana token pair information"""
    __tablename__ = 'token_pairs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    pair_address = Column(String(44), unique=True, nullable=False, index=True)
    chain_id = Column(String(20), nullable=False, default='solana')
    dex_id = Column(String(50), nullable=False)
    
    # Token information
    base_token_address = Column(String(44), nullable=False, index=True)
    base_token_name = Column(String(100))
    base_token_symbol = Column(String(20))
    quote_token_address = Column(String(44), nullable=False)
    quote_token_name = Column(String(100))
    quote_token_symbol = Column(String(20))
    
    # Pair metadata
    pair_created_at = Column(DateTime)
    first_seen_at = Column(DateTime, default=datetime.utcnow)
    last_updated_at = Column(DateTime, default=datetime.utcnow)
    
    # Current state
    is_active = Column(Boolean, default=True)
    
    # Relationships
    price_history = relationship("PriceHistory", back_populates="token_pair", cascade="all, delete-orphan")
    classifications = relationship("TokenClassification", back_populates="token_pair", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<TokenPair({self.base_token_symbol}/{self.quote_token_symbol})>"

class PriceHistory(Base):
    """Model for storing historical price and volume data"""
    __tablename__ = 'price_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    pair_id = Column(Integer, ForeignKey('token_pairs.id'), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Price data
    price_native = Column(Float)
    price_usd = Column(Float)
    
    # Volume data
    volume_5m = Column(Float)
    volume_1h = Column(Float)
    volume_6h = Column(Float)
    volume_24h = Column(Float)
    
    # Market data
    market_cap = Column(Float)
    fdv = Column(Float)  # Fully Diluted Valuation
    liquidity_usd = Column(Float)
    
    # Trading metrics
    txns_5m_buys = Column(Integer)
    txns_5m_sells = Column(Integer)
    txns_1h_buys = Column(Integer)
    txns_1h_sells = Column(Integer)
    txns_6h_buys = Column(Integer)
    txns_6h_sells = Column(Integer)
    txns_24h_buys = Column(Integer)
    txns_24h_sells = Column(Integer)
    
    # Price change percentages
    price_change_5m = Column(Float)
    price_change_1h = Column(Float)
    price_change_6h = Column(Float)
    price_change_24h = Column(Float)
    
    # Relationship
    token_pair = relationship("TokenPair", back_populates="price_history")
    
    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_pair_timestamp', 'pair_id', 'timestamp'),
        Index('idx_timestamp', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<PriceHistory(pair_id={self.pair_id}, price_usd={self.price_usd}, timestamp={self.timestamp})>"

class TokenClassification(Base):
    """Model for storing AI classification results"""
    __tablename__ = 'token_classifications'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    pair_id = Column(Integer, ForeignKey('token_pairs.id'), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Classification results
    classification = Column(String(20), nullable=False)  # 'normal', 'pump', 'rug', 'new_pair'
    confidence_score = Column(Float, nullable=False)
    
    # Feature values used for classification
    features = Column(Text)  # JSON string of feature values
    
    # Additional metadata
    model_version = Column(String(50))
    analysis_window_start = Column(DateTime)
    analysis_window_end = Column(DateTime)
    
    # Alert status
    alert_sent = Column(Boolean, default=False)
    alert_sent_at = Column(DateTime)
    
    # Relationship
    token_pair = relationship("TokenPair", back_populates="classifications")
    
    # Indexes
    __table_args__ = (
        Index('idx_pair_classification', 'pair_id', 'classification'),
        Index('idx_classification_timestamp', 'classification', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<TokenClassification(pair_id={self.pair_id}, classification={self.classification}, confidence={self.confidence_score})>"

class PatternAnalysis(Base):
    """Model for storing pattern analysis results"""
    __tablename__ = 'pattern_analysis'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Pattern information
    pattern_type = Column(String(50), nullable=False)  # 'pump_pattern', 'rug_pattern', 'volume_spike', etc.
    pattern_description = Column(Text)
    
    # Pattern metrics
    frequency = Column(Integer)  # How often this pattern occurs
    success_rate = Column(Float)  # Success rate of predictions using this pattern
    avg_confidence = Column(Float)  # Average confidence score
    
    # Pattern parameters (JSON string)
    pattern_parameters = Column(Text)
    
    # Statistical data
    sample_size = Column(Integer)
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<PatternAnalysis(pattern_type={self.pattern_type}, frequency={self.frequency})>"

class ModelPerformance(Base):
    """Model for tracking AI model performance metrics"""
    __tablename__ = 'model_performance'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Model information
    model_version = Column(String(50), nullable=False)
    model_type = Column(String(50), nullable=False)  # 'classification', 'regression', etc.
    
    # Performance metrics
    accuracy = Column(Float)
    precision = Column(Float)
    recall = Column(Float)
    f1_score = Column(Float)
    
    # Class-specific metrics (JSON string)
    class_metrics = Column(Text)
    
    # Training information
    training_samples = Column(Integer)
    validation_samples = Column(Integer)
    training_duration = Column(Float)  # in seconds
    
    def __repr__(self):
        return f"<ModelPerformance(model_version={self.model_version}, accuracy={self.accuracy})>"

class AlertLog(Base):
    """Model for logging alerts and notifications"""
    __tablename__ = 'alert_log'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Alert information
    alert_type = Column(String(50), nullable=False)  # 'pump_detected', 'rug_detected', 'new_pair'
    pair_address = Column(String(44), nullable=False, index=True)
    token_symbol = Column(String(20))
    
    # Alert details
    message = Column(Text)
    confidence_score = Column(Float)
    
    # Delivery information
    delivery_method = Column(String(50))  # 'console', 'file', 'telegram', 'discord'
    delivery_status = Column(String(20), default='pending')  # 'pending', 'sent', 'failed'
    delivery_attempts = Column(Integer, default=0)
    
    def __repr__(self):
        return f"<AlertLog(alert_type={self.alert_type}, token_symbol={self.token_symbol})>"