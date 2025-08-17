import os
from dataclasses import dataclass
from typing import Dict, List
from dotenv import load_dotenv

load_dotenv()

@dataclass
class APIConfig:
    """Configuration for DexScreener API"""
    BASE_URL: str = "https://api.dexscreener.com/latest"
    REQUEST_TIMEOUT: int = 30
    RATE_LIMIT_DELAY: float = 0.5  # seconds between requests
    MAX_RETRIES: int = 3
    
@dataclass
class DatabaseConfig:
    """Database configuration"""
    DATABASE_URL: str = "sqlite:///solana_tokens.db"
    ECHO_SQL: bool = False
    
@dataclass
class AIConfig:
    """AI model configuration"""
    # Thresholds for classification
    PUMP_PRICE_THRESHOLD: float = 0.5  # 50% price increase
    RUG_PRICE_THRESHOLD: float = -0.8  # 80% price decrease
    VOLUME_SPIKE_THRESHOLD: float = 10.0  # 10x volume increase
    
    # Time windows for analysis
    SHORT_TERM_WINDOW: int = 300  # 5 minutes in seconds
    MEDIUM_TERM_WINDOW: int = 3600  # 1 hour in seconds
    LONG_TERM_WINDOW: int = 86400  # 24 hours in seconds
    
    # Model parameters
    FEATURE_WINDOW_SIZE: int = 100  # Number of data points for feature extraction
    MODEL_UPDATE_INTERVAL: int = 3600  # Update model every hour
    CONFIDENCE_THRESHOLD: float = 0.7  # Minimum confidence for predictions
    
@dataclass
class MonitoringConfig:
    """Monitoring and alerting configuration"""
    CHECK_INTERVAL: int = 60  # Check for new tokens every minute
    NEW_PAIR_AGE_THRESHOLD: int = 3600  # Consider pairs new if created within 1 hour
    LOG_LEVEL: str = "INFO"
    MAX_LOG_SIZE: int = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT: int = 5
    
@dataclass
class SolanaConfig:
    """Solana-specific configuration"""
    CHAIN_ID: str = "solana"
    MIN_LIQUIDITY_USD: float = 1000.0  # Minimum liquidity to consider
    MIN_VOLUME_24H_USD: float = 10000.0  # Minimum 24h volume to consider
    
# Global configuration instances
API_CONFIG = APIConfig()
DB_CONFIG = DatabaseConfig()
AI_CONFIG = AIConfig()
MONITORING_CONFIG = MonitoringConfig()
SOLANA_CONFIG = SolanaConfig()

# Feature extraction configuration
FEATURES_CONFIG = {
    "price_features": [
        "price_change_5m", "price_change_1h", "price_change_24h",
        "price_volatility_5m", "price_volatility_1h"
    ],
    "volume_features": [
        "volume_change_5m", "volume_change_1h", "volume_change_24h",
        "volume_spike_ratio", "volume_trend"
    ],
    "liquidity_features": [
        "liquidity_change_5m", "liquidity_change_1h", "liquidity_change_24h",
        "liquidity_to_volume_ratio"
    ],
    "market_features": [
        "market_cap_change", "fdv_change", "pair_age_hours",
        "transaction_count_5m", "unique_wallets_5m"
    ]
}

# Classification labels
CLASSIFICATION_LABELS = {
    0: "normal",
    1: "pump",
    2: "rug",
    3: "new_pair"
}