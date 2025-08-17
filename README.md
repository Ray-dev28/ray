# Solana Token Analysis Bot

A comprehensive Python bot that fetches data from DexScreener, focusing exclusively on Solana tokens. The bot uses AI to analyze and save every token that got rugged, pumped, or represents new pairs, with advanced filtering and blacklisting capabilities to identify patterns and avoid scams.

## Features

### 🔍 **Data Fetching**
- Real-time data fetching from DexScreener API
- Exclusive focus on Solana blockchain tokens
- Comprehensive token pair information collection
- Historical price and volume tracking

### 🤖 **AI Analysis**
- Pattern recognition for pump and dump schemes
- Rug pull detection algorithms
- New pair identification and analysis
- Machine learning models for predictive analysis

### 🛡️ **Advanced Filtering System**
- **Coin Blacklist**: Automatically blacklist known scam tokens
- **Developer Blacklist**: Track and blacklist malicious developers
- **Fake Volume Detection**: Integration with Pocket Universe API algorithm
- **Risk Assessment**: Multi-factor risk scoring system
- **Pattern Matching**: Regex-based filtering for suspicious names/symbols

### 📊 **Volume Analysis**
- Pocket Universe API integration for fake volume detection
- Wash trading pattern recognition
- Volume-price correlation analysis
- Suspicious trading behavior identification

### 🔒 **Contract Verification**
- RugCheck.xyz API integration for contract safety verification
- Only interact with contracts marked as "Good"
- Bundle detection and automatic blacklisting
- Security feature analysis (mint/freeze authority, liquidity locks)
- Holder distribution analysis

### 🗄️ **Data Storage**
- SQLite database with comprehensive schema
- Historical data preservation
- Pattern analysis storage
- Performance metrics tracking

## Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd solana-token-bot
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. **Initialize the database**
```bash
python -c "from database.database import init_database; init_database()"
```

## Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
# Database Configuration
DATABASE_URL=sqlite:///solana_tokens.db

# Logging Configuration
LOG_LEVEL=INFO

# AI Model Configuration
MODEL_SAVE_PATH=./models/
MODEL_BACKUP_PATH=./models/backups/

# Pocket Universe API Configuration (Optional)
POCKET_UNIVERSE_API_KEY=your_pocket_universe_api_key_here

# RugCheck.xyz API Configuration (Optional)
RUGCHECK_API_KEY=your_rugcheck_api_key_here

# Optional: External Services
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
DISCORD_WEBHOOK_URL=your_discord_webhook_here
```

### Filter Configuration

The bot includes comprehensive filtering options in `config.py`:

```python
# General filtering criteria
ENABLE_FILTERS: bool = True
MIN_MARKET_CAP_USD: float = 50000.0
MAX_MARKET_CAP_USD: float = 100000000.0
MIN_AGE_HOURS: float = 0.5
MAX_AGE_HOURS: float = 168.0

# Fake volume detection
ENABLE_FAKE_VOLUME_DETECTION: bool = True
FAKE_VOLUME_THRESHOLD: float = 0.7
VOLUME_ANOMALY_THRESHOLD: float = 5.0

# RugCheck contract verification
ENABLE_RUGCHECK: bool = True
ONLY_GOOD_CONTRACTS: bool = True
BUNDLE_DETECTION_THRESHOLD: float = 70.0
```

## Blacklist Management

### Coin Blacklist
Automatically managed list of known scam tokens:
- Pattern-based detection (SCAM, TEST, FAKE, etc.)
- Manual additions
- Auto-detection based on behavior analysis

### Developer Blacklist
Track malicious developers across projects:
- Known rug pull developers
- Repeat offenders
- Auto-detection based on patterns

### Trusted Lists
Maintain whitelists for legitimate tokens and developers:
- Major Solana tokens (SOL, USDC, USDT)
- Verified developers
- Trusted DEX platforms

## Usage

### Basic Usage

```python
from filters.filter_manager import filter_manager
from utils.blacklist_utils import BlacklistUtils

# Apply filters to token data
result = filter_manager.apply_filters(token_data)
if result.passed:
    print("Token passed all filters")
else:
    print(f"Token filtered: {result.reason}")

# Async filtering with fake volume detection
result = await filter_manager.apply_filters_async(token_data)
```

### Command Line Tools

#### Blacklist Management
```bash
# Export blacklists
python utils/blacklist_utils.py --export blacklists_backup.json

# Import blacklists
python utils/blacklist_utils.py --import blacklists_backup.json

# Show summary
python utils/blacklist_utils.py --summary

# Add coin to blacklist
python utils/blacklist_utils.py --add-coin TOKEN_ADDRESS --reason "Confirmed rug pull"

# Validate integrity
python utils/blacklist_utils.py --validate
```

#### RugCheck Verification
```bash
# Verify single token contract
python utils/rugcheck_utils.py --verify TOKEN_ADDRESS

# Batch verify tokens from file
python utils/rugcheck_utils.py --batch-verify tokens.txt

# Detect and blacklist bundled tokens
python utils/rugcheck_utils.py --detect-bundles tokens.txt

# Comprehensive security analysis
python utils/rugcheck_utils.py --analyze-security TOKEN_ADDRESS

# Show RugCheck statistics
python utils/rugcheck_utils.py --stats
```

### Fake Volume Detection

The bot integrates with Pocket Universe API and includes internal algorithms:

```python
from filters.fake_volume_detector import fake_volume_detector

async with fake_volume_detector as detector:
    analysis = await detector.analyze_volume(token_data)
    if analysis.is_fake:
        print(f"Fake volume detected: {analysis.confidence_score:.2f}")
        print(f"Reasons: {', '.join(analysis.reasons)}")
```

### RugCheck Contract Verification

The bot integrates with RugCheck.xyz for comprehensive contract analysis:

```python
from filters.rugcheck_analyzer import rugcheck_analyzer

async with rugcheck_analyzer as analyzer:
    result = await analyzer.analyze_token(token_address)
    if not result.is_good_contract:
        print(f"Contract not safe: {result.status}")
    if result.is_bundled:
        print(f"Bundled supply: {result.bundle_percentage:.1f}%")
```

## Database Schema

### Token Pairs
- Comprehensive token pair information
- DEX and chain data
- Creation timestamps
- Activity status

### Price History
- Historical price data across multiple timeframes
- Volume metrics (5m, 1h, 6h, 24h)
- Transaction counts
- Market cap and liquidity data

### Classifications
- AI-generated token classifications
- Confidence scores
- Feature analysis results
- Alert status tracking

### Pattern Analysis
- Identified patterns and their success rates
- Statistical analysis results
- Model performance metrics

## Filtering Criteria

### Risk Factors
1. **Market Cap**: Too low or too high
2. **Age**: Too new or too old
3. **Liquidity**: Insufficient liquidity
4. **Volume**: Suspicious volume patterns
5. **Trading**: Unusual trading behavior
6. **Names**: Suspicious token names/symbols

### Automatic Blacklisting
Tokens are automatically blacklisted for:
- Fake volume detection (confidence > 70%)
- Wash trading patterns
- Suspicious developer activity
- Pattern matching scam indicators
- RugCheck contract verification failures
- Bundle detection (>70% supply held by single address)
- Contracts not marked as "Good" by RugCheck

### Volume Analysis Methods
1. **Pocket Universe API**: External verification
2. **Internal Analysis**: Volume pattern detection
3. **Wash Trading**: Balanced buy/sell detection
4. **Price Correlation**: Volume vs price movement analysis

## API Integration

### DexScreener API
- Real-time token data fetching
- Solana-specific endpoints
- Rate limiting and error handling

### Pocket Universe API
- Fake volume verification
- Wash trading detection
- Volume legitimacy scoring

### RugCheck.xyz API
- Contract safety verification
- Bundle detection and analysis
- Security feature verification
- Holder distribution analysis

## Monitoring and Alerts

### Alert Types
- New pair detection
- Pump detection
- Rug pull detection
- Fake volume detection

### Delivery Methods
- Console logging
- File logging
- Telegram notifications (optional)
- Discord webhooks (optional)

## Performance Optimization

### Caching
- Volume analysis results cached for 5 minutes
- Filter results optimization
- Database query optimization

### Async Processing
- Concurrent token analysis
- Non-blocking API calls
- Efficient batch processing

## Security Features

### Input Validation
- Address format validation
- Data sanitization
- SQL injection prevention

### Rate Limiting
- API request throttling
- Error handling and retries
- Graceful degradation

## Development

### Project Structure
```
├── config.py              # Configuration settings
├── database/
│   ├── models.py          # SQLAlchemy models
│   └── database.py        # Database management
├── filters/
│   ├── filter_manager.py  # Main filtering logic
│   ├── blacklist_manager.py # Blacklist management
│   └── fake_volume_detector.py # Volume analysis
├── utils/
│   └── blacklist_utils.py # Utility functions
└── README.md
```

### Adding New Filters
1. Create filter function in `filter_manager.py`
2. Add configuration options in `config.py`
3. Update filter application logic
4. Add tests and documentation

### Contributing
1. Fork the repository
2. Create feature branch
3. Add tests for new functionality
4. Submit pull request with documentation

## Troubleshooting

### Common Issues
1. **Database Connection**: Check DATABASE_URL in .env
2. **API Timeouts**: Adjust timeout settings in config
3. **Memory Usage**: Implement cache cleanup for large datasets
4. **Rate Limiting**: Ensure proper delays between API calls

### Logging
Set LOG_LEVEL in .env to DEBUG for detailed logging:
```env
LOG_LEVEL=DEBUG
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This bot is for educational and research purposes only. Always do your own research before making any investment decisions. The developers are not responsible for any financial losses incurred through the use of this software.

## Support

For support, please open an issue on the GitHub repository or contact the development team.

---

**⚠️ Important**: Always keep your blacklists updated and regularly review auto-detected entries to ensure accuracy.
