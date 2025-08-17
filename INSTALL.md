# 🚀 Solana Token Analysis Bot - Installation Guide

Complete step-by-step installation and setup guide for the Solana Token Analysis Bot with trading capabilities.

## 📋 Prerequisites

Before installing the bot, ensure you have:

- **Python 3.8+** installed on your system
- **Git** for cloning the repository
- **Telegram account** for notifications and trading
- **Solana wallet** for trading operations
- **Basic terminal/command line knowledge**

## 🛠️ Step 1: System Setup

### For Windows:

1. **Install Python 3.8+**
   - Download from [python.org](https://python.org)
   - Make sure to check "Add Python to PATH" during installation

2. **Install Git**
   - Download from [git-scm.com](https://git-scm.com)

3. **Open Command Prompt or PowerShell as Administrator**

### For macOS:

1. **Install Homebrew** (if not already installed)
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

2. **Install Python and Git**
   ```bash
   brew install python3 git
   ```

### For Linux (Ubuntu/Debian):

```bash
sudo apt update
sudo apt install python3 python3-pip git python3-venv
```

## 📥 Step 2: Download the Bot

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/solana-token-bot.git
   cd solana-token-bot
   ```

2. **Verify the download**
   ```bash
   ls -la
   ```
   You should see files like `main.py`, `config.py`, `requirements.txt`, etc.

## 🔧 Step 3: Create Virtual Environment

**Why use a virtual environment?** It keeps the bot's dependencies separate from your system Python.

### Create and activate virtual environment:

**Windows:**
```cmd
python -m venv bot_env
bot_env\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv bot_env
source bot_env/bin/activate
```

You should see `(bot_env)` at the beginning of your command prompt.

## 📦 Step 4: Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**If you encounter errors:**
- On Windows: Try `python -m pip install -r requirements.txt`
- On Linux: You might need `sudo apt install python3-dev build-essential`

## 🔑 Step 5: Create Telegram Bot

### 5.1 Create Bot with BotFather

1. **Open Telegram** and search for `@BotFather`
2. **Start conversation** and send `/newbot`
3. **Choose a name** for your bot (e.g., "My Solana Bot")
4. **Choose a username** (must end with 'bot', e.g., "mysolanabot")
5. **Save the bot token** (looks like `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 5.2 Get Your Chat ID

1. **Send a message** to your newly created bot
2. **Open this URL** in your browser (replace `YOUR_BOT_TOKEN`):
   ```
   https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates
   ```
3. **Find your chat ID** in the response (it's the number after `"chat":{"id":`)

### 5.3 Test Your Bot (Optional)

Send this URL to verify everything works:
```
https://api.telegram.org/botYOUR_BOT_TOKEN/sendMessage?chat_id=YOUR_CHAT_ID&text=Hello%20World
```

## 🔐 Step 6: Configure Environment Variables

1. **Copy the example environment file**
   ```bash
   cp .env .env.local
   ```

2. **Edit the configuration file**
   
   **Windows:** `notepad .env.local`
   **macOS:** `nano .env.local`
   **Linux:** `nano .env.local`

3. **Fill in your credentials:**

```env
# Database Configuration
DATABASE_URL=sqlite:///solana_tokens.db
LOG_LEVEL=INFO

# Telegram Configuration (Required)
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789

# ToxiSol Trading Configuration
TOXISOL_BOT_USERNAME=@ToxiSolBot
SOLANA_WALLET_ADDRESS=your_wallet_address_here
SOLANA_PRIVATE_KEY=your_private_key_here

# API Keys (Optional but recommended)
RUGCHECK_API_KEY=your_rugcheck_api_key_here
POCKET_UNIVERSE_API_KEY=your_pocket_universe_api_key_here
```

### 🔒 **SECURITY WARNING:**
- **Never share your private key** with anyone
- **Keep your .env.local file secure** and never commit it to version control
- **Use a dedicated wallet** for trading, not your main wallet

## 🗄️ Step 7: Initialize Database

```bash
python -c "from database.database import init_database; init_database()"
```

You should see: `Database tables created successfully`

## 🧪 Step 8: Test Configuration

### 8.1 Test Basic Configuration
```bash
python -c "from config import *; print('✅ Configuration loaded successfully')"
```

### 8.2 Test Telegram Connection
```bash
python -c "
import asyncio
from trading.telegram_trader import telegram_trader

async def test():
    async with telegram_trader as trader:
        await trader._send_telegram_message('🧪 Test message from Solana Bot!')

asyncio.run(test())
"
```

### 8.3 Test Database Connection
```bash
python -c "
from database.database import db_manager
print('Database health:', db_manager.health_check())
"
```

## 🚀 Step 9: Run the Bot

### 9.1 First Run (Test Mode)

```bash
python main.py
```

**What you should see:**
```
🤖 Solana Token Analysis Bot
==================================================
2024-01-15 10:30:00,123 - __main__ - INFO - 🚀 Starting Solana Token Analysis Bot
2024-01-15 10:30:00,456 - __main__ - INFO - ✅ Database initialized
2024-01-15 10:30:01,789 - __main__ - INFO - 🔄 Starting monitoring loop
```

### 9.2 Check Telegram

You should receive a startup notification in your Telegram chat:

```
🚀 Solana Token Bot Started

Startup Time: 2024-01-15 10:30:00 UTC

Configuration:
• Filters: ✅ Enabled
• RugCheck: ✅ Enabled
• Fake Volume Detection: ✅ Enabled
• Check Interval: 60s

🤖 Bot is now monitoring Solana tokens!
```

## 🔧 Step 10: Configuration Tuning

### 10.1 Edit Bot Settings

Edit `config.py` to customize:

```python
# Monitoring frequency (seconds)
CHECK_INTERVAL: int = 60  # Check every minute

# Trading amounts
DEFAULT_BUY_AMOUNT: float = 0.1  # 0.1 SOL per trade

# Risk thresholds
FAKE_VOLUME_THRESHOLD: float = 0.7  # 70% confidence
BUNDLE_DETECTION_THRESHOLD: float = 70.0  # 70% supply
```

### 10.2 Blacklist Management

**Add tokens to blacklist:**
```bash
python utils/blacklist_utils.py --add-coin TOKEN_ADDRESS --reason "Confirmed scam"
```

**Check blacklist status:**
```bash
python utils/blacklist_utils.py --summary
```

### 10.3 RugCheck Integration

**Verify a token:**
```bash
python utils/rugcheck_utils.py --verify TOKEN_ADDRESS
```

**Batch verify tokens:**
```bash
echo "TOKEN_ADDRESS_1" > tokens.txt
echo "TOKEN_ADDRESS_2" >> tokens.txt
python utils/rugcheck_utils.py --batch-verify tokens.txt
```

## 🔄 Step 11: Running as a Service

### 11.1 Create a Startup Script

**Windows (create `start_bot.bat`):**
```batch
@echo off
cd /d "C:\path\to\solana-token-bot"
call bot_env\Scripts\activate
python main.py
pause
```

**macOS/Linux (create `start_bot.sh`):**
```bash
#!/bin/bash
cd /path/to/solana-token-bot
source bot_env/bin/activate
python main.py
```

Make it executable:
```bash
chmod +x start_bot.sh
```

### 11.2 Run in Background (Linux/macOS)

**Using screen:**
```bash
screen -S solana-bot
./start_bot.sh
# Press Ctrl+A, then D to detach
```

**To reattach:**
```bash
screen -r solana-bot
```

**Using nohup:**
```bash
nohup ./start_bot.sh > bot.log 2>&1 &
```

## 📊 Step 12: Monitoring and Maintenance

### 12.1 Check Bot Status

**View logs:**
```bash
tail -f logs/bot.log
```

**Check database stats:**
```bash
python -c "
from database.database import db_manager
from database.models import *
with db_manager.get_session() as session:
    print('Token pairs:', session.query(TokenPair).count())
    print('Price records:', session.query(PriceHistory).count())
"
```

### 12.2 Backup Your Data

**Backup database:**
```bash
cp solana_tokens.db solana_tokens_backup_$(date +%Y%m%d).db
```

**Backup blacklists:**
```bash
python utils/blacklist_utils.py --export blacklists_backup_$(date +%Y%m%d).json
```

## 🚨 Troubleshooting

### Common Issues:

**1. "Module not found" error:**
```bash
# Make sure virtual environment is activated
source bot_env/bin/activate  # Linux/macOS
# or
bot_env\Scripts\activate     # Windows
```

**2. Telegram notifications not working:**
- Verify bot token and chat ID
- Check that you've sent at least one message to the bot
- Test with the URL method in Step 5.3

**3. Database errors:**
```bash
# Recreate database
rm solana_tokens.db
python -c "from database.database import init_database; init_database()"
```

**4. API rate limiting:**
- Increase `RATE_LIMIT_DELAY` in config.py
- Reduce `CHECK_INTERVAL` frequency

**5. High memory usage:**
- The bot automatically cleans up old data
- Restart the bot daily using a cron job

### Getting Help:

1. **Check logs:** `tail -f logs/bot.log`
2. **Enable debug logging:** Set `LOG_LEVEL=DEBUG` in .env.local
3. **Test individual components:** Use the test commands in Step 8

## 🎯 Step 13: Advanced Configuration

### 13.1 Custom Trading Strategies

Edit the `_evaluate_trading_opportunity` method in `main.py`:

```python
# Example: Only trade tokens with high volume
if (volume_24h > 500000 and  # $500k+ volume
    price_change_24h > 100 and  # 100%+ pump
    liquidity_usd > 100000):    # $100k+ liquidity
    # Execute trade
```

### 13.2 Multiple Wallets

You can run multiple instances with different wallets:

1. **Create separate directories**
2. **Use different .env.local files**
3. **Use different database files**
4. **Use different Telegram bots**

### 13.3 Risk Management

```python
# In config.py, adjust these values:
MAX_DAILY_TRADES = 10        # Maximum trades per day
MAX_POSITION_SIZE = 1.0      # Maximum SOL per position
STOP_LOSS_PERCENTAGE = -50   # Stop loss at -50%
TAKE_PROFIT_PERCENTAGE = 200 # Take profit at +200%
```

## ✅ Final Checklist

- [ ] Python 3.8+ installed
- [ ] Virtual environment created and activated
- [ ] Dependencies installed successfully
- [ ] Telegram bot created and configured
- [ ] Environment variables set correctly
- [ ] Database initialized
- [ ] Bot starts without errors
- [ ] Telegram notifications working
- [ ] Blacklist management tested
- [ ] RugCheck integration working (if API key provided)

## 🎉 You're Ready!

Your Solana Token Analysis Bot is now ready to:

- ✅ Monitor Solana tokens in real-time
- ✅ Apply advanced filtering and risk assessment
- ✅ Detect fake volume and bundled tokens
- ✅ Verify contracts with RugCheck
- ✅ Execute trades via ToxiSol
- ✅ Send notifications for all activities
- ✅ Maintain comprehensive logs and statistics

## 📞 Support

If you encounter issues:

1. **Check the troubleshooting section above**
2. **Review the logs in `logs/bot.log`**
3. **Test individual components using the provided commands**
4. **Ensure all API keys and credentials are correct**

**Remember:** Always test with small amounts first and never risk more than you can afford to lose!

---

**⚠️ Disclaimer:** This bot is for educational purposes. Always do your own research before making any trades. The developers are not responsible for any financial losses.