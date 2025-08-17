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

@dataclass
class FilterConfig:
    """Filtering and blacklist configuration"""
    # General filtering criteria
    ENABLE_FILTERS: bool = True
    MIN_MARKET_CAP_USD: float = 50000.0  # Minimum market cap to consider
    MAX_MARKET_CAP_USD: float = 100000000.0  # Maximum market cap to consider
    MIN_AGE_HOURS: float = 0.5  # Minimum token age in hours
    MAX_AGE_HOURS: float = 168.0  # Maximum token age in hours (7 days)
    
    # Volume and liquidity filters
    MIN_LIQUIDITY_RATIO: float = 0.1  # Min liquidity/volume ratio
    MAX_PRICE_IMPACT_PERCENT: float = 10.0  # Max price impact for $1000 trade
    MIN_HOLDERS_COUNT: int = 10  # Minimum number of holders
    
    # Trading filters
    MIN_TRANSACTIONS_5M: int = 5  # Minimum transactions in 5 minutes
    MIN_UNIQUE_WALLETS_5M: int = 3  # Minimum unique wallets in 5 minutes
    MAX_SINGLE_WALLET_PERCENTAGE: float = 50.0  # Max percentage owned by single wallet
    
    # Risk filters
    ENABLE_HONEYPOT_CHECK: bool = True
    ENABLE_RUG_RISK_CHECK: bool = True
    MAX_DEV_WALLET_PERCENTAGE: float = 20.0  # Max percentage held by dev wallet
    REQUIRE_VERIFIED_CONTRACT: bool = False
    REQUIRE_AUDIT: bool = False
    
    # Social filters
    MIN_TELEGRAM_MEMBERS: int = 0
    MIN_TWITTER_FOLLOWERS: int = 0
    REQUIRE_WEBSITE: bool = False
    
    # Fake volume detection
    ENABLE_FAKE_VOLUME_DETECTION: bool = True
    FAKE_VOLUME_THRESHOLD: float = 0.7  # Confidence threshold for fake volume detection
    VOLUME_ANOMALY_THRESHOLD: float = 5.0  # Threshold for volume anomaly detection

@dataclass
class PocketUniverseConfig:
    """Pocket Universe API configuration for fake volume detection"""
    ENABLE_POCKET_UNIVERSE: bool = True
    API_BASE_URL: str = "https://api.pocketuniverse.app"
    API_TIMEOUT: int = 10
    MAX_RETRIES: int = 3
    CACHE_DURATION: int = 300  # Cache results for 5 minutes
    
    # Fake volume detection endpoints
    VOLUME_CHECK_ENDPOINT: str = "/v1/volume/verify"
    TOKEN_ANALYSIS_ENDPOINT: str = "/v1/token/analyze"
    WASH_TRADING_ENDPOINT: str = "/v1/trading/wash-detection"

# Global configuration instances
API_CONFIG = APIConfig()
DB_CONFIG = DatabaseConfig()
AI_CONFIG = AIConfig()
MONITORING_CONFIG = MonitoringConfig()
SOLANA_CONFIG = SolanaConfig()
FILTER_CONFIG = FilterConfig()
POCKET_UNIVERSE_CONFIG = PocketUniverseConfig()

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

# Blacklists Configuration
COIN_BLACKLIST = [
    # Known scam tokens (add token addresses here)
    # Example: "TokenAddressHere1234567890123456789012345",
    
    # Common scam patterns (partial matches)
    "SCAM",
    "TEST",
    "FAKE",
    "COPY",
    "CLONE",
]

DEV_BLACKLIST = [
    # Known scammer/rug pull developer wallet addresses
    # Example: "DevWalletAddress1234567890123456789012345",
    
    # Add known malicious developer addresses here
    # These should be full wallet addresses
]

# Token symbol blacklist patterns
SYMBOL_BLACKLIST_PATTERNS = [
    r".*SCAM.*",
    r".*TEST.*",
    r".*FAKE.*",
    r".*BOT.*",
    r".*COPY.*",
    r".*CLONE.*",
    r"^\$.*",  # Tokens starting with $
    r".*MOON.*",
    r".*100X.*",
    r".*1000X.*",
]

# Token name blacklist patterns
NAME_BLACKLIST_PATTERNS = [
    r".*scam.*",
    r".*test.*",
    r".*fake.*",
    r".*copy.*",
    r".*clone.*",
    r".*airdrop.*",
    r".*free.*",
    r".*giveaway.*",
    r".*presale.*",
    r".*private sale.*",
]

# Risky token patterns
RISKY_PATTERNS = {
    "suspicious_names": [
        r".*elon.*",
        r".*musk.*",
        r".*doge.*killer.*",
        r".*shib.*killer.*",
        r".*safe.*",
        r".*moon.*",
        r".*rocket.*",
        r".*diamond.*hands.*",
    ],
    "pump_indicators": [
        r".*pump.*",
        r".*moon.*",
        r".*rocket.*",
        r".*lambo.*",
        r".*100x.*",
        r".*1000x.*",
        r".*to.*moon.*",
    ]
}

# Whitelist for trusted tokens (optional)
TRUSTED_TOKENS = [
    # Major Solana tokens that should never be filtered
    "So11111111111111111111111111111111111111112",  # Wrapped SOL
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
    # Add other trusted token addresses
]

# DEX whitelist - trusted DEXs
TRUSTED_DEXS = [
    "raydium",
    "orca",
    "jupiter",
    "serum",
    "aldrin",
    "saber",
    "mercurial",
    "lifinity",
]