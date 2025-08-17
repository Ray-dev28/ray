#!/usr/bin/env python3
"""
Solana Token Analysis Bot

A comprehensive bot that analyzes Solana tokens from DexScreener,
detects patterns, applies filters, and executes trades via Telegram.
"""

import asyncio
import logging
import signal
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json

# Import all components
from config import (
    MONITORING_CONFIG, AI_CONFIG, FILTER_CONFIG, 
    RUGCHECK_CONFIG, POCKET_UNIVERSE_CONFIG
)
from database.database import init_database, db_manager
from api.dexscreener_client import dexscreener_client
from filters.filter_manager import filter_manager
from filters.blacklist_manager import blacklist_manager
from trading.telegram_trader import telegram_trader
from utils.blacklist_utils import BlacklistUtils

# Configure logging
def setup_logging():
    """Setup comprehensive logging configuration"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Create logs directory
    import os
    os.makedirs('logs', exist_ok=True)
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, MONITORING_CONFIG.LOG_LEVEL),
        format=log_format,
        handlers=[
            logging.FileHandler('logs/bot.log', mode='a'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Set specific logger levels
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)

class SolanaTokenBot:
    """Main bot orchestration class"""
    
    def __init__(self):
        self.running = False
        self.startup_time = datetime.utcnow()
        self.processed_tokens = set()
        self.analysis_stats = {
            'total_analyzed': 0,
            'pumps_detected': 0,
            'rugs_detected': 0,
            'new_pairs_found': 0,
            'fake_volume_detected': 0,
            'bundled_tokens_detected': 0,
            'trades_executed': 0,
            'alerts_sent': 0
        }
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("SolanaTokenBot initialized")
    
    async def start(self):
        """Start the bot"""
        self.logger.info("🚀 Starting Solana Token Analysis Bot")
        
        try:
            # Initialize database
            init_database()
            self.logger.info("✅ Database initialized")
            
            # Send startup notification
            await self._send_startup_notification()
            
            # Set running flag
            self.running = True
            
            # Start main monitoring loop
            await self._run_monitoring_loop()
            
        except Exception as e:
            self.logger.error(f"❌ Failed to start bot: {e}")
            await self._send_error_notification(f"Bot startup failed: {e}")
            raise
    
    async def stop(self):
        """Stop the bot gracefully"""
        self.logger.info("🛑 Stopping Solana Token Analysis Bot")
        self.running = False
        
        # Send shutdown notification
        await self._send_shutdown_notification()
        
        # Close database connections
        db_manager.close()
        
        self.logger.info("✅ Bot stopped successfully")
    
    async def _run_monitoring_loop(self):
        """Main monitoring and analysis loop"""
        self.logger.info("🔄 Starting monitoring loop")
        
        while self.running:
            try:
                # Get current time
                start_time = time.time()
                
                # Fetch new tokens
                await self._fetch_and_analyze_tokens()
                
                # Perform periodic maintenance
                await self._periodic_maintenance()
                
                # Calculate processing time
                processing_time = time.time() - start_time
                self.logger.info(f"⏱️  Processing cycle completed in {processing_time:.2f}s")
                
                # Wait for next cycle
                sleep_time = max(0, MONITORING_CONFIG.CHECK_INTERVAL - processing_time)
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                
            except Exception as e:
                self.logger.error(f"❌ Error in monitoring loop: {e}")
                await self._send_error_notification(f"Monitoring loop error: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def _fetch_and_analyze_tokens(self):
        """Fetch and analyze tokens from DexScreener"""
        try:
            self.logger.info("📡 Fetching tokens from DexScreener")
            
            async with dexscreener_client as client:
                # Get new pairs
                new_pairs = await client.get_new_pairs(hours=1)
                
                # Get trending tokens
                trending_tokens = await client.get_trending_tokens()
                
                # Combine and deduplicate
                all_tokens = []
                seen_addresses = set()
                
                for token_list in [new_pairs or [], trending_tokens or []]:
                    for token in token_list:
                        token_address = token.get('baseToken', {}).get('address')
                        if token_address and token_address not in seen_addresses:
                            all_tokens.append(token)
                            seen_addresses.add(token_address)
                
                # Filter Solana tokens
                solana_tokens = await client.filter_solana_tokens(all_tokens)
                
                self.logger.info(f"🔍 Found {len(solana_tokens)} Solana tokens to analyze")
                
                # Analyze each token
                await self._analyze_token_batch(solana_tokens)
                
        except Exception as e:
            self.logger.error(f"❌ Error fetching tokens: {e}")
    
    async def _analyze_token_batch(self, tokens: List[Dict]):
        """Analyze a batch of tokens"""
        if not tokens:
            return
        
        self.logger.info(f"🧪 Analyzing batch of {len(tokens)} tokens")
        
        for token in tokens:
            try:
                await self._analyze_single_token(token)
                
                # Small delay between analyses
                await asyncio.sleep(0.1)
                
            except Exception as e:
                token_address = token.get('baseToken', {}).get('address', 'unknown')
                self.logger.error(f"❌ Error analyzing token {token_address}: {e}")
    
    async def _analyze_single_token(self, token_data: Dict):
        """Analyze a single token comprehensively"""
        try:
            base_token = token_data.get('baseToken', {})
            token_address = base_token.get('address')
            token_symbol = base_token.get('symbol', 'Unknown')
            
            if not token_address or token_address in self.processed_tokens:
                return
            
            self.logger.debug(f"🔬 Analyzing token {token_symbol} ({token_address})")
            
            # Apply comprehensive filters (includes RugCheck, fake volume, etc.)
            filter_result = await filter_manager.apply_filters_async(token_data)
            
            self.analysis_stats['total_analyzed'] += 1
            
            if not filter_result.passed:
                self.logger.info(f"❌ Token {token_symbol} filtered out: {filter_result.reason}")
                
                # Send alert for detected issues
                await self._send_filtered_token_alert(token_data, filter_result)
                
                # Track specific filter reasons
                self._update_filter_stats(filter_result)
                
                # Mark as processed
                self.processed_tokens.add(token_address)
                return
            
            # Token passed filters - analyze for trading opportunities
            trading_decision = await self._evaluate_trading_opportunity(token_data, filter_result)
            
            if trading_decision['should_trade']:
                await self._execute_trade_decision(token_data, trading_decision)
            
            # Send analysis notification
            await self._send_analysis_notification(token_data, filter_result, trading_decision)
            
            # Mark as processed
            self.processed_tokens.add(token_address)
            
        except Exception as e:
            self.logger.error(f"❌ Error in single token analysis: {e}")
    
    async def _evaluate_trading_opportunity(self, token_data: Dict, filter_result) -> Dict:
        """Evaluate if token presents a trading opportunity"""
        try:
            base_token = token_data.get('baseToken', {})
            token_symbol = base_token.get('symbol', 'Unknown')
            
            # Get price and volume data
            price_usd = float(token_data.get('priceUsd', 0))
            volume_24h = token_data.get('volume', {}).get('h24', 0)
            price_change_24h = token_data.get('priceChange', {}).get('h24', 0)
            liquidity_usd = token_data.get('liquidity', {}).get('usd', 0)
            
            # Trading decision logic
            decision = {
                'should_trade': False,
                'action': None,
                'amount_sol': 0,
                'confidence': 0,
                'reasons': []
            }
            
            # Check for pump opportunity
            if (price_change_24h > 50 and 
                volume_24h > 100000 and 
                liquidity_usd > 50000 and
                filter_result.risk_score < 0.3):
                
                decision.update({
                    'should_trade': True,
                    'action': 'buy',
                    'amount_sol': 0.1,  # Conservative amount
                    'confidence': 0.7,
                    'reasons': ['Strong pump detected with good liquidity']
                })
                
                self.logger.info(f"🚀 Trading opportunity identified: {token_symbol}")
            
            # Check for new pair opportunity
            pair_created_at = token_data.get('pairCreatedAt')
            if pair_created_at:
                pair_age_hours = (time.time() * 1000 - pair_created_at) / (1000 * 3600)
                
                if (pair_age_hours < 2 and 
                    volume_24h > 50000 and 
                    liquidity_usd > 20000 and
                    filter_result.risk_score < 0.4):
                    
                    decision.update({
                        'should_trade': True,
                        'action': 'buy',
                        'amount_sol': 0.05,  # Smaller amount for new pairs
                        'confidence': 0.6,
                        'reasons': ['New pair with good initial metrics']
                    })
                    
                    self.logger.info(f"🆕 New pair opportunity: {token_symbol}")
            
            return decision
            
        except Exception as e:
            self.logger.error(f"❌ Error evaluating trading opportunity: {e}")
            return {'should_trade': False, 'action': None, 'amount_sol': 0, 'confidence': 0, 'reasons': []}
    
    async def _execute_trade_decision(self, token_data: Dict, decision: Dict):
        """Execute trading decision"""
        try:
            base_token = token_data.get('baseToken', {})
            token_address = base_token.get('address')
            token_symbol = base_token.get('symbol', 'Unknown')
            
            self.logger.info(f"💰 Executing {decision['action']} for {token_symbol}")
            
            async with telegram_trader as trader:
                if decision['action'] == 'buy':
                    result = await trader.buy_token(
                        token_address=token_address,
                        amount_sol=decision['amount_sol'],
                        slippage=5.0
                    )
                else:  # sell
                    result = await trader.sell_token(
                        token_address=token_address,
                        slippage=5.0
                    )
                
                if result.success:
                    self.analysis_stats['trades_executed'] += 1
                    self.logger.info(f"✅ Trade executed successfully: {result.transaction_hash}")
                else:
                    self.logger.error(f"❌ Trade failed: {result.error_message}")
            
        except Exception as e:
            self.logger.error(f"❌ Error executing trade: {e}")
    
    async def _send_filtered_token_alert(self, token_data: Dict, filter_result):
        """Send alert for filtered tokens"""
        try:
            base_token = token_data.get('baseToken', {})
            token_symbol = base_token.get('symbol', 'Unknown')
            
            # Determine alert type based on filter reason
            alert_type = 'filtered'
            if 'fake volume' in filter_result.reason.lower():
                alert_type = 'fake_volume'
                self.analysis_stats['fake_volume_detected'] += 1
            elif 'bundled' in filter_result.reason.lower():
                alert_type = 'bundle'
                self.analysis_stats['bundled_tokens_detected'] += 1
            elif 'rug' in filter_result.reason.lower():
                alert_type = 'rug'
                self.analysis_stats['rugs_detected'] += 1
            
            # Send notification
            async with telegram_trader as trader:
                await trader.send_alert_notification(
                    alert_type=alert_type,
                    token_data=token_data,
                    analysis_result={
                        'reason': filter_result.reason,
                        'confidence_score': filter_result.risk_score,
                        'warnings': filter_result.warnings
                    }
                )
            
            self.analysis_stats['alerts_sent'] += 1
            
        except Exception as e:
            self.logger.error(f"❌ Error sending filtered token alert: {e}")
    
    async def _send_analysis_notification(self, token_data: Dict, filter_result, trading_decision: Dict):
        """Send analysis notification for passed tokens"""
        try:
            if not trading_decision['should_trade']:
                return  # Only notify for trading opportunities
            
            base_token = token_data.get('baseToken', {})
            token_symbol = base_token.get('symbol', 'Unknown')
            
            async with telegram_trader as trader:
                await trader.send_alert_notification(
                    alert_type='opportunity',
                    token_data=token_data,
                    analysis_result={
                        'reason': f"Trading opportunity: {', '.join(trading_decision['reasons'])}",
                        'confidence_score': trading_decision['confidence'],
                        'action': trading_decision['action'],
                        'amount': trading_decision['amount_sol']
                    }
                )
            
        except Exception as e:
            self.logger.error(f"❌ Error sending analysis notification: {e}")
    
    def _update_filter_stats(self, filter_result):
        """Update filter statistics"""
        reason = filter_result.reason.lower()
        
        if 'pump' in reason:
            self.analysis_stats['pumps_detected'] += 1
        elif 'rug' in reason:
            self.analysis_stats['rugs_detected'] += 1
        elif 'fake volume' in reason:
            self.analysis_stats['fake_volume_detected'] += 1
        elif 'bundled' in reason or 'bundle' in reason:
            self.analysis_stats['bundled_tokens_detected'] += 1
    
    async def _periodic_maintenance(self):
        """Perform periodic maintenance tasks"""
        try:
            current_time = datetime.utcnow()
            
            # Send hourly statistics
            if current_time.minute == 0:
                await self._send_statistics_report()
            
            # Clean up old processed tokens (every 6 hours)
            if current_time.hour % 6 == 0 and current_time.minute == 0:
                await self._cleanup_processed_tokens()
            
            # Clean up old blacklist entries (daily at midnight)
            if current_time.hour == 0 and current_time.minute == 0:
                BlacklistUtils.cleanup_old_auto_detections(30)
            
        except Exception as e:
            self.logger.error(f"❌ Error in periodic maintenance: {e}")
    
    async def _cleanup_processed_tokens(self):
        """Clean up old processed tokens to prevent memory issues"""
        try:
            # Keep only recent tokens (last 24 hours worth)
            max_tokens = MONITORING_CONFIG.CHECK_INTERVAL * 24  # Rough estimate
            
            if len(self.processed_tokens) > max_tokens:
                # Remove oldest half
                tokens_to_remove = len(self.processed_tokens) // 2
                tokens_list = list(self.processed_tokens)
                
                for token in tokens_list[:tokens_to_remove]:
                    self.processed_tokens.discard(token)
                
                self.logger.info(f"🧹 Cleaned up {tokens_to_remove} old processed tokens")
            
        except Exception as e:
            self.logger.error(f"❌ Error cleaning up processed tokens: {e}")
    
    async def _send_startup_notification(self):
        """Send bot startup notification"""
        try:
            async with telegram_trader as trader:
                message = f"""
🚀 <b>Solana Token Bot Started</b>

<b>Startup Time:</b> {self.startup_time.strftime('%Y-%m-%d %H:%M:%S')} UTC

<b>Configuration:</b>
• Filters: {'✅ Enabled' if FILTER_CONFIG.ENABLE_FILTERS else '❌ Disabled'}
• RugCheck: {'✅ Enabled' if RUGCHECK_CONFIG.ENABLE_RUGCHECK else '❌ Disabled'}
• Fake Volume Detection: {'✅ Enabled' if FILTER_CONFIG.ENABLE_FAKE_VOLUME_DETECTION else '❌ Disabled'}
• Check Interval: {MONITORING_CONFIG.CHECK_INTERVAL}s

<b>Features:</b>
• 🔍 Real-time token analysis
• 🛡️ Advanced filtering system
• 📦 Bundle detection
• ⚠️ Fake volume detection
• 💰 Automated trading
• 📊 Pattern recognition

🤖 <i>Bot is now monitoring Solana tokens!</i>
                """.strip()
                
                await trader._send_telegram_message(message)
            
        except Exception as e:
            self.logger.error(f"❌ Error sending startup notification: {e}")
    
    async def _send_shutdown_notification(self):
        """Send bot shutdown notification"""
        try:
            uptime = datetime.utcnow() - self.startup_time
            
            async with telegram_trader as trader:
                message = f"""
🛑 <b>Solana Token Bot Stopped</b>

<b>Shutdown Time:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
<b>Uptime:</b> {str(uptime).split('.')[0]}

<b>Session Statistics:</b>
• Tokens Analyzed: {self.analysis_stats['total_analyzed']}
• Alerts Sent: {self.analysis_stats['alerts_sent']}
• Trades Executed: {self.analysis_stats['trades_executed']}
• Fake Volume Detected: {self.analysis_stats['fake_volume_detected']}
• Bundled Tokens: {self.analysis_stats['bundled_tokens_detected']}

🤖 <i>Bot shutdown completed successfully.</i>
                """.strip()
                
                await trader._send_telegram_message(message)
            
        except Exception as e:
            self.logger.error(f"❌ Error sending shutdown notification: {e}")
    
    async def _send_statistics_report(self):
        """Send hourly statistics report"""
        try:
            async with telegram_trader as trader:
                await trader.send_statistics_report()
                
                # Also send analysis stats
                uptime = datetime.utcnow() - self.startup_time
                
                message = f"""
📈 <b>Analysis Statistics</b>

<b>Uptime:</b> {str(uptime).split('.')[0]}

<b>Analysis Results:</b>
• Total Analyzed: {self.analysis_stats['total_analyzed']}
• Pumps Detected: {self.analysis_stats['pumps_detected']}
• Rugs Detected: {self.analysis_stats['rugs_detected']}
• New Pairs Found: {self.analysis_stats['new_pairs_found']}
• Fake Volume: {self.analysis_stats['fake_volume_detected']}
• Bundled Tokens: {self.analysis_stats['bundled_tokens_detected']}

<b>Actions:</b>
• Trades Executed: {self.analysis_stats['trades_executed']}
• Alerts Sent: {self.analysis_stats['alerts_sent']}

<b>Memory:</b>
• Processed Tokens: {len(self.processed_tokens)}

⏰ <i>Hourly report - {datetime.utcnow().strftime('%H:%M')} UTC</i>
                """.strip()
                
                await trader._send_telegram_message(message)
            
        except Exception as e:
            self.logger.error(f"❌ Error sending statistics report: {e}")
    
    async def _send_error_notification(self, error_message: str):
        """Send error notification"""
        try:
            async with telegram_trader as trader:
                message = f"""
🚨 <b>Bot Error</b>

<b>Error:</b> {error_message}
<b>Time:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC

⚠️ <i>Please check logs for more details.</i>
                """.strip()
                
                await trader._send_telegram_message(message)
            
        except Exception as e:
            self.logger.error(f"❌ Error sending error notification: {e}")

# Global bot instance
bot = SolanaTokenBot()

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    print(f"\n🛑 Received signal {signum}, shutting down...")
    bot.running = False

async def main():
    """Main entry point"""
    # Setup logging
    setup_logging()
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Start the bot
        await bot.start()
        
    except KeyboardInterrupt:
        print("\n🛑 Keyboard interrupt received")
    except Exception as e:
        logging.error(f"❌ Fatal error: {e}")
        sys.exit(1)
    finally:
        # Ensure clean shutdown
        await bot.stop()

if __name__ == "__main__":
    print("🤖 Solana Token Analysis Bot")
    print("=" * 50)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Failed to start bot: {e}")
        sys.exit(1)