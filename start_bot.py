#!/usr/bin/env python3
"""
Solana Token Bot Startup Script

This script provides a user-friendly interface for starting and managing the bot.
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def print_banner():
    """Print bot banner"""
    print("🤖 Solana Token Analysis Bot")
    print("=" * 50)
    print("Advanced Solana token monitoring and trading bot")
    print("Features: AI Analysis | RugCheck | Fake Volume Detection | Automated Trading")
    print("=" * 50)
    print()

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Error: Python 3.8+ is required")
        print(f"Current version: {version.major}.{version.minor}.{version.micro}")
        print("Please upgrade Python and try again.")
        return False
    
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} - Compatible")
    return True

def check_virtual_environment():
    """Check if running in virtual environment"""
    in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    
    if not in_venv:
        print("⚠️  Warning: Not running in virtual environment")
        print("It's recommended to use a virtual environment:")
        print("  python -m venv bot_env")
        if platform.system() == "Windows":
            print("  bot_env\\Scripts\\activate")
        else:
            print("  source bot_env/bin/activate")
        print()
        
        response = input("Continue anyway? (y/N): ").lower()
        if response != 'y':
            return False
    else:
        print("✅ Virtual environment detected")
    
    return True

def check_requirements():
    """Check if required packages are installed"""
    print("🔍 Checking dependencies...")
    
    required_packages = [
        'aiohttp', 'requests', 'pandas', 'numpy', 'sqlalchemy',
        'python-dotenv', 'asyncio-throttle', 'pydantic'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing packages: {', '.join(missing_packages)}")
        print("Installing missing dependencies...")
        
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + missing_packages)
            print("✅ Dependencies installed successfully")
        except subprocess.CalledProcessError:
            print("❌ Failed to install dependencies")
            print("Please run: pip install -r requirements.txt")
            return False
    else:
        print("✅ All dependencies satisfied")
    
    return True

def check_configuration():
    """Check if configuration files exist"""
    print("🔧 Checking configuration...")
    
    env_file = Path('.env.local')
    if not env_file.exists():
        env_example = Path('.env')
        if env_example.exists():
            print("⚠️  .env.local not found, copying from .env")
            import shutil
            shutil.copy('.env', '.env.local')
        else:
            print("❌ Configuration file not found")
            print("Please create .env.local with your configuration")
            return False
    
    # Check if critical variables are set
    from dotenv import load_dotenv
    load_dotenv('.env.local')
    
    critical_vars = ['TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID']
    missing_vars = []
    
    for var in critical_vars:
        value = os.getenv(var)
        if not value or value.startswith('your_'):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"⚠️  Missing configuration: {', '.join(missing_vars)}")
        print("Please edit .env.local and add your credentials")
        
        response = input("Continue anyway? (y/N): ").lower()
        if response != 'y':
            return False
    else:
        print("✅ Configuration appears complete")
    
    return True

def check_database():
    """Check and initialize database if needed"""
    print("🗄️  Checking database...")
    
    db_file = Path('solana_tokens.db')
    if not db_file.exists():
        print("Database not found, initializing...")
        try:
            from database.database import init_database
            init_database()
            print("✅ Database initialized successfully")
        except Exception as e:
            print(f"❌ Database initialization failed: {e}")
            return False
    else:
        print("✅ Database exists")
    
    return True

def test_telegram_connection():
    """Test Telegram bot connection"""
    print("📱 Testing Telegram connection...")
    
    try:
        import asyncio
        from trading.telegram_trader import telegram_trader
        
        async def test():
            try:
                async with telegram_trader as trader:
                    await trader._send_telegram_message("🧪 Bot startup test - Connection successful!")
                return True
            except Exception as e:
                print(f"❌ Telegram test failed: {e}")
                return False
        
        result = asyncio.run(test())
        if result:
            print("✅ Telegram connection successful")
        return result
        
    except Exception as e:
        print(f"⚠️  Telegram test skipped: {e}")
        return True  # Don't fail startup for this

def show_startup_menu():
    """Show startup options menu"""
    print("\n🚀 Startup Options:")
    print("1. Start bot normally")
    print("2. Start with debug logging")
    print("3. Run configuration test only")
    print("4. View current configuration")
    print("5. Exit")
    
    while True:
        try:
            choice = input("\nSelect option (1-5): ").strip()
            if choice in ['1', '2', '3', '4', '5']:
                return int(choice)
            else:
                print("Invalid choice. Please enter 1-5.")
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            sys.exit(0)

def view_configuration():
    """Display current configuration (without sensitive data)"""
    print("\n📋 Current Configuration:")
    print("-" * 30)
    
    from dotenv import load_dotenv
    load_dotenv('.env.local')
    
    config_items = [
        ('Database URL', os.getenv('DATABASE_URL', 'Not set')),
        ('Log Level', os.getenv('LOG_LEVEL', 'INFO')),
        ('Telegram Bot', '✅ Configured' if os.getenv('TELEGRAM_BOT_TOKEN') else '❌ Not configured'),
        ('Chat ID', '✅ Set' if os.getenv('TELEGRAM_CHAT_ID') else '❌ Not set'),
        ('RugCheck API', '✅ Set' if os.getenv('RUGCHECK_API_KEY') else '❌ Not set'),
        ('Pocket Universe API', '✅ Set' if os.getenv('POCKET_UNIVERSE_API_KEY') else '❌ Not set'),
        ('Solana Wallet', '✅ Set' if os.getenv('SOLANA_WALLET_ADDRESS') else '❌ Not set'),
    ]
    
    for key, value in config_items:
        print(f"{key:20}: {value}")
    
    print("-" * 30)

def start_bot(debug_mode=False):
    """Start the main bot"""
    print("\n🚀 Starting Solana Token Analysis Bot...")
    
    if debug_mode:
        os.environ['LOG_LEVEL'] = 'DEBUG'
        print("🐛 Debug mode enabled")
    
    try:
        from main import main
        import asyncio
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Bot crashed: {e}")
        print("Check logs/bot.log for details")

def main():
    """Main startup function"""
    print_banner()
    
    # System checks
    if not check_python_version():
        sys.exit(1)
    
    if not check_virtual_environment():
        sys.exit(1)
    
    if not check_requirements():
        sys.exit(1)
    
    if not check_configuration():
        sys.exit(1)
    
    if not check_database():
        sys.exit(1)
    
    # Show menu
    while True:
        choice = show_startup_menu()
        
        if choice == 1:
            # Test Telegram connection before starting
            if test_telegram_connection():
                start_bot(debug_mode=False)
            break
        
        elif choice == 2:
            # Test Telegram connection before starting
            if test_telegram_connection():
                start_bot(debug_mode=True)
            break
        
        elif choice == 3:
            print("\n✅ Configuration test completed successfully!")
            print("All systems appear to be working correctly.")
            break
        
        elif choice == 4:
            view_configuration()
            continue
        
        elif choice == 5:
            print("👋 Goodbye!")
            break

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Startup failed: {e}")
        sys.exit(1)