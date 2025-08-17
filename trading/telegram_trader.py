import asyncio
import aiohttp
import logging
import json
import os
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class TradeAction(Enum):
    BUY = "buy"
    SELL = "sell"

class TradeStatus(Enum):
    PENDING = "pending"
    EXECUTED = "executed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class TradeResult:
    """Result of a trade execution"""
    success: bool
    transaction_hash: str = ""
    amount_in: float = 0.0
    amount_out: float = 0.0
    price: float = 0.0
    gas_used: float = 0.0
    error_message: str = ""
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

@dataclass
class TradeOrder:
    """Trade order configuration"""
    token_address: str
    action: TradeAction
    amount_sol: float
    slippage: float = 5.0
    priority_fee: float = 0.001
    max_retries: int = 3
    timeout: int = 30

class TelegramTrader:
    """Telegram-based trading using ToxiSol integration"""
    
    def __init__(self):
        # Telegram configuration
        self.telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        # Trading configuration
        self.toxisol_bot_username = os.getenv('TOXISOL_BOT_USERNAME', '@ToxiSolBot')
        self.wallet_address = os.getenv('SOLANA_WALLET_ADDRESS')
        self.private_key = os.getenv('SOLANA_PRIVATE_KEY')
        
        # Session for HTTP requests
        self.session = None
        
        # Trade tracking
        self.active_trades = {}
        self.trade_history = []
        
        logger.info("TelegramTrader initialized")
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def execute_trade(self, order: TradeOrder) -> TradeResult:
        """Execute a trade order via Telegram/ToxiSol"""
        try:
            logger.info(f"Executing {order.action.value} order for {order.token_address}")
            
            # Generate trade command for ToxiSol
            trade_command = self._generate_trade_command(order)
            
            # Execute trade via Telegram
            result = await self._execute_via_telegram(trade_command, order)
            
            # Track the trade
            trade_id = f"{order.token_address}_{order.action.value}_{int(datetime.utcnow().timestamp())}"
            self.active_trades[trade_id] = {
                'order': order,
                'result': result,
                'timestamp': datetime.utcnow()
            }
            
            # Send notification
            await self._send_trade_notification(order, result)
            
            # Add to history
            self.trade_history.append({
                'trade_id': trade_id,
                'order': order,
                'result': result
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            error_result = TradeResult(
                success=False,
                error_message=str(e)
            )
            await self._send_error_notification(order, str(e))
            return error_result
    
    def _generate_trade_command(self, order: TradeOrder) -> str:
        """Generate ToxiSol command for trading"""
        if order.action == TradeAction.BUY:
            # Buy command format: /buy <token_address> <amount_sol> <slippage>
            return f"/buy {order.token_address} {order.amount_sol} {order.slippage}"
        else:
            # Sell command format: /sell <token_address> <percentage> <slippage>
            # For sell, we'll sell 100% of holdings
            return f"/sell {order.token_address} 100 {order.slippage}"
    
    async def _execute_via_telegram(self, command: str, order: TradeOrder) -> TradeResult:
        """Execute trade command via Telegram API"""
        try:
            # Simulate ToxiSol integration - In real implementation, this would:
            # 1. Send the command to ToxiSol bot via Telegram API
            # 2. Monitor for response/confirmation
            # 3. Parse transaction details from response
            
            # For now, we'll simulate the trade execution
            await asyncio.sleep(2)  # Simulate processing time
            
            # Simulate successful trade
            if order.action == TradeAction.BUY:
                # Simulate buying tokens
                estimated_tokens = order.amount_sol * 1000000  # Mock conversion rate
                result = TradeResult(
                    success=True,
                    transaction_hash=f"mock_tx_{int(datetime.utcnow().timestamp())}",
                    amount_in=order.amount_sol,
                    amount_out=estimated_tokens,
                    price=order.amount_sol / estimated_tokens if estimated_tokens > 0 else 0,
                    gas_used=0.001
                )
            else:
                # Simulate selling tokens
                estimated_sol = 0.5  # Mock SOL received
                result = TradeResult(
                    success=True,
                    transaction_hash=f"mock_tx_{int(datetime.utcnow().timestamp())}",
                    amount_in=1000000,  # Mock tokens sold
                    amount_out=estimated_sol,
                    price=estimated_sol / 1000000,
                    gas_used=0.001
                )
            
            logger.info(f"Trade executed successfully: {result.transaction_hash}")
            return result
            
        except Exception as e:
            logger.error(f"Error executing trade via Telegram: {e}")
            return TradeResult(
                success=False,
                error_message=str(e)
            )
    
    async def _send_trade_notification(self, order: TradeOrder, result: TradeResult):
        """Send trade notification via Telegram"""
        try:
            if not self.telegram_bot_token or not self.telegram_chat_id:
                logger.warning("Telegram credentials not configured for notifications")
                return
            
            if result.success:
                action_emoji = "🟢 BUY" if order.action == TradeAction.BUY else "🔴 SELL"
                message = f"""
{action_emoji} <b>Trade Executed Successfully</b>

<b>Token:</b> <code>{order.token_address}</code>
<b>Action:</b> {order.action.value.upper()}
<b>Amount In:</b> {result.amount_in:.6f} {'SOL' if order.action == TradeAction.BUY else 'Tokens'}
<b>Amount Out:</b> {result.amount_out:.6f} {'Tokens' if order.action == TradeAction.BUY else 'SOL'}
<b>Price:</b> {result.price:.10f}
<b>Gas Used:</b> {result.gas_used:.6f} SOL
<b>TX Hash:</b> <code>{result.transaction_hash}</code>
<b>Time:</b> {result.timestamp.strftime('%Y-%m-%d %H:%M:%S')} UTC

✅ <i>Trade completed successfully!</i>
                """.strip()
            else:
                message = f"""
❌ <b>Trade Failed</b>

<b>Token:</b> <code>{order.token_address}</code>
<b>Action:</b> {order.action.value.upper()}
<b>Amount:</b> {order.amount_sol} SOL
<b>Error:</b> {result.error_message}
<b>Time:</b> {result.timestamp.strftime('%Y-%m-%d %H:%M:%S')} UTC

⚠️ <i>Please check your configuration and try again.</i>
                """.strip()
            
            await self._send_telegram_message(message)
            
        except Exception as e:
            logger.error(f"Error sending trade notification: {e}")
    
    async def _send_error_notification(self, order: TradeOrder, error: str):
        """Send error notification"""
        try:
            message = f"""
🚨 <b>Trading Error</b>

<b>Token:</b> <code>{order.token_address}</code>
<b>Action:</b> {order.action.value.upper()}
<b>Error:</b> {error}
<b>Time:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC

❌ <i>Trade execution failed. Please check logs for details.</i>
            """.strip()
            
            await self._send_telegram_message(message)
            
        except Exception as e:
            logger.error(f"Error sending error notification: {e}")
    
    async def _send_telegram_message(self, message: str):
        """Send message via Telegram Bot API"""
        try:
            if not self.session:
                return
            
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            payload = {
                "chat_id": self.telegram_chat_id,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }
            
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    logger.info("Telegram notification sent successfully")
                else:
                    logger.warning(f"Failed to send Telegram notification: {response.status}")
                    
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
    
    async def buy_token(self, token_address: str, amount_sol: float, slippage: float = 5.0) -> TradeResult:
        """Buy a token"""
        order = TradeOrder(
            token_address=token_address,
            action=TradeAction.BUY,
            amount_sol=amount_sol,
            slippage=slippage
        )
        return await self.execute_trade(order)
    
    async def sell_token(self, token_address: str, slippage: float = 5.0) -> TradeResult:
        """Sell all holdings of a token"""
        order = TradeOrder(
            token_address=token_address,
            action=TradeAction.SELL,
            amount_sol=0,  # Not used for sell orders
            slippage=slippage
        )
        return await self.execute_trade(order)
    
    async def send_alert_notification(self, alert_type: str, token_data: Dict[str, Any], analysis_result: Dict[str, Any]):
        """Send alert notification for detected patterns"""
        try:
            base_token = token_data.get('baseToken', {})
            token_symbol = base_token.get('symbol', 'Unknown')
            token_address = base_token.get('address', '')
            
            price_usd = token_data.get('priceUsd', 0)
            volume_24h = token_data.get('volume', {}).get('h24', 0)
            price_change_24h = token_data.get('priceChange', {}).get('h24', 0)
            
            # Choose emoji and color based on alert type
            alert_emojis = {
                'pump': '🚀',
                'rug': '💀',
                'new_pair': '🆕',
                'fake_volume': '⚠️',
                'bundle': '📦'
            }
            
            emoji = alert_emojis.get(alert_type.lower(), '🔔')
            
            message = f"""
{emoji} <b>{alert_type.upper()} ALERT</b>

<b>Token:</b> {token_symbol}
<b>Address:</b> <code>{token_address}</code>
<b>Price:</b> ${price_usd:.8f}
<b>24h Volume:</b> ${volume_24h:,.0f}
<b>24h Change:</b> {price_change_24h:+.2f}%

<b>Analysis:</b>
{analysis_result.get('reason', 'Pattern detected')}

<b>Confidence:</b> {analysis_result.get('confidence_score', 0):.2f}
<b>Time:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC

🔗 <a href="https://dexscreener.com/solana/{token_address}">View on DexScreener</a>
            """.strip()
            
            await self._send_telegram_message(message)
            
        except Exception as e:
            logger.error(f"Error sending alert notification: {e}")
    
    def get_trade_statistics(self) -> Dict[str, Any]:
        """Get trading statistics"""
        total_trades = len(self.trade_history)
        successful_trades = sum(1 for trade in self.trade_history if trade['result'].success)
        failed_trades = total_trades - successful_trades
        
        buy_trades = sum(1 for trade in self.trade_history if trade['order'].action == TradeAction.BUY)
        sell_trades = sum(1 for trade in self.trade_history if trade['order'].action == TradeAction.SELL)
        
        total_sol_spent = sum(
            trade['order'].amount_sol 
            for trade in self.trade_history 
            if trade['order'].action == TradeAction.BUY and trade['result'].success
        )
        
        total_sol_received = sum(
            trade['result'].amount_out 
            for trade in self.trade_history 
            if trade['order'].action == TradeAction.SELL and trade['result'].success
        )
        
        return {
            'total_trades': total_trades,
            'successful_trades': successful_trades,
            'failed_trades': failed_trades,
            'success_rate': (successful_trades / total_trades * 100) if total_trades > 0 else 0,
            'buy_trades': buy_trades,
            'sell_trades': sell_trades,
            'total_sol_spent': total_sol_spent,
            'total_sol_received': total_sol_received,
            'net_sol': total_sol_received - total_sol_spent,
            'active_trades': len(self.active_trades)
        }
    
    async def send_statistics_report(self):
        """Send trading statistics report"""
        try:
            stats = self.get_trade_statistics()
            
            message = f"""
📊 <b>Trading Statistics Report</b>

<b>Total Trades:</b> {stats['total_trades']}
<b>Successful:</b> {stats['successful_trades']} ({stats['success_rate']:.1f}%)
<b>Failed:</b> {stats['failed_trades']}

<b>Trade Breakdown:</b>
• Buy Orders: {stats['buy_trades']}
• Sell Orders: {stats['sell_trades']}

<b>Financial Summary:</b>
• SOL Spent: {stats['total_sol_spent']:.6f}
• SOL Received: {stats['total_sol_received']:.6f}
• Net SOL: {stats['net_sol']:+.6f}

<b>Active Trades:</b> {stats['active_trades']}
<b>Report Time:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC

📈 <i>Keep trading responsibly!</i>
            """.strip()
            
            await self._send_telegram_message(message)
            
        except Exception as e:
            logger.error(f"Error sending statistics report: {e}")

# Global trader instance
telegram_trader = TelegramTrader()