import re
import logging
import asyncio
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

from config import (
    FILTER_CONFIG, COIN_BLACKLIST, DEV_BLACKLIST, 
    SYMBOL_BLACKLIST_PATTERNS, NAME_BLACKLIST_PATTERNS,
    RISKY_PATTERNS, TRUSTED_TOKENS, TRUSTED_DEXS
)
from filters.fake_volume_detector import fake_volume_detector, VolumeAnalysisResult
from filters.blacklist_manager import blacklist_manager

logger = logging.getLogger(__name__)

@dataclass
class FilterResult:
    """Result of filtering operation"""
    passed: bool
    reason: Optional[str] = None
    risk_score: float = 0.0
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []

class TokenFilterManager:
    """Manages all token filtering operations including blacklists and criteria"""
    
    def __init__(self):
        self.coin_blacklist = set(COIN_BLACKLIST)
        self.dev_blacklist = set(DEV_BLACKLIST)
        self.symbol_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in SYMBOL_BLACKLIST_PATTERNS]
        self.name_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in NAME_BLACKLIST_PATTERNS]
        self.risky_name_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in RISKY_PATTERNS["suspicious_names"]]
        self.pump_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in RISKY_PATTERNS["pump_indicators"]]
        self.trusted_tokens = set(TRUSTED_TOKENS)
        self.trusted_dexs = set(TRUSTED_DEXS)
        
        logger.info("TokenFilterManager initialized")
    
    def apply_filters(self, token_data: Dict[str, Any]) -> FilterResult:
        """Apply all filters to a token and return the result"""
        
        if not FILTER_CONFIG.ENABLE_FILTERS:
            return FilterResult(passed=True, reason="Filters disabled")
        
        # Skip filtering for trusted tokens
        token_address = token_data.get('baseToken', {}).get('address', '')
        if token_address in self.trusted_tokens:
            return FilterResult(passed=True, reason="Trusted token")
        
        # Initialize result
        result = FilterResult(passed=True, warnings=[])
        
        # Apply blacklist filters
        blacklist_result = self._check_blacklists(token_data)
        if not blacklist_result.passed:
            return blacklist_result
        result.warnings.extend(blacklist_result.warnings)
        result.risk_score += blacklist_result.risk_score
        
        # Apply basic criteria filters
        criteria_result = self._check_basic_criteria(token_data)
        if not criteria_result.passed:
            return criteria_result
        result.warnings.extend(criteria_result.warnings)
        result.risk_score += criteria_result.risk_score
        
        # Apply risk assessment
        risk_result = self._assess_risk(token_data)
        result.warnings.extend(risk_result.warnings)
        result.risk_score += risk_result.risk_score
        
        # Apply trading filters
        trading_result = self._check_trading_criteria(token_data)
        if not trading_result.passed:
            return trading_result
        result.warnings.extend(trading_result.warnings)
        result.risk_score += trading_result.risk_score
        
        # Final risk assessment
        if result.risk_score > 0.8:
            return FilterResult(
                passed=False,
                reason=f"High risk score: {result.risk_score:.2f}",
                risk_score=result.risk_score,
                warnings=result.warnings
            )
        
        return result
    
    async def apply_filters_async(self, token_data: Dict[str, Any]) -> FilterResult:
        """Apply all filters including async fake volume detection"""
        
        # First apply synchronous filters
        sync_result = self.apply_filters(token_data)
        if not sync_result.passed:
            return sync_result
        
        # Apply fake volume detection if enabled
        if FILTER_CONFIG.ENABLE_FAKE_VOLUME_DETECTION:
            volume_result = await self._check_fake_volume(token_data)
            if not volume_result.passed:
                # Auto-blacklist tokens with fake volume
                token_address = token_data.get('baseToken', {}).get('address', '')
                if token_address:
                    blacklist_manager.add_coin_to_blacklist(
                        token_address, 
                        f"Fake volume detected: {volume_result.reason}",
                        auto_detected=True
                    )
                return volume_result
            
            sync_result.warnings.extend(volume_result.warnings)
            sync_result.risk_score += volume_result.risk_score
        
        return sync_result
    
    def _check_blacklists(self, token_data: Dict[str, Any]) -> FilterResult:
        """Check token and dev against blacklists"""
        result = FilterResult(passed=True, warnings=[])
        
        base_token = token_data.get('baseToken', {})
        token_address = base_token.get('address', '')
        token_symbol = base_token.get('symbol', '').upper()
        token_name = base_token.get('name', '').lower()
        
        # Check coin blacklist (exact matches)
        if token_address in self.coin_blacklist:
            return FilterResult(
                passed=False,
                reason="Token address in blacklist",
                risk_score=1.0
            )
        
        # Check for blacklisted substrings in address
        for blacklisted_item in self.coin_blacklist:
            if isinstance(blacklisted_item, str) and len(blacklisted_item) < 20:  # Pattern, not full address
                if blacklisted_item.upper() in token_symbol or blacklisted_item.lower() in token_name:
                    return FilterResult(
                        passed=False,
                        reason=f"Token contains blacklisted pattern: {blacklisted_item}",
                        risk_score=1.0
                    )
        
        # Check symbol patterns
        for pattern in self.symbol_patterns:
            if pattern.match(token_symbol):
                return FilterResult(
                    passed=False,
                    reason=f"Token symbol matches blacklisted pattern: {pattern.pattern}",
                    risk_score=1.0
                )
        
        # Check name patterns
        for pattern in self.name_patterns:
            if pattern.match(token_name):
                return FilterResult(
                    passed=False,
                    reason=f"Token name matches blacklisted pattern: {pattern.pattern}",
                    risk_score=1.0
                )
        
        # Check dev blacklist (if creator info available)
        creator_address = token_data.get('creator', '') or token_data.get('deployer', '')
        if creator_address and creator_address in self.dev_blacklist:
            return FilterResult(
                passed=False,
                reason="Developer address in blacklist",
                risk_score=1.0
            )
        
        return result
    
    def _check_basic_criteria(self, token_data: Dict[str, Any]) -> FilterResult:
        """Check basic filtering criteria like market cap, age, etc."""
        result = FilterResult(passed=True, warnings=[])
        
        # Market cap filter
        market_cap = token_data.get('marketCap')
        if market_cap is not None:
            if market_cap < FILTER_CONFIG.MIN_MARKET_CAP_USD:
                return FilterResult(
                    passed=False,
                    reason=f"Market cap too low: ${market_cap:,.0f}",
                    risk_score=0.3
                )
            if market_cap > FILTER_CONFIG.MAX_MARKET_CAP_USD:
                return FilterResult(
                    passed=False,
                    reason=f"Market cap too high: ${market_cap:,.0f}",
                    risk_score=0.1
                )
        
        # Liquidity filter
        liquidity = token_data.get('liquidity', {}).get('usd', 0)
        if liquidity < FILTER_CONFIG.MIN_LIQUIDITY_USD:
            return FilterResult(
                passed=False,
                reason=f"Liquidity too low: ${liquidity:,.0f}",
                risk_score=0.4
            )
        
        # Volume filter
        volume_24h = token_data.get('volume', {}).get('h24', 0)
        if volume_24h < FILTER_CONFIG.MIN_VOLUME_24H_USD:
            result.warnings.append(f"Low 24h volume: ${volume_24h:,.0f}")
            result.risk_score += 0.2
        
        # Age filter
        pair_created_at = token_data.get('pairCreatedAt')
        if pair_created_at:
            try:
                created_time = datetime.fromtimestamp(pair_created_at / 1000)
                age_hours = (datetime.utcnow() - created_time).total_seconds() / 3600
                
                if age_hours < FILTER_CONFIG.MIN_AGE_HOURS:
                    result.warnings.append(f"Very new token: {age_hours:.1f} hours old")
                    result.risk_score += 0.3
                
                if age_hours > FILTER_CONFIG.MAX_AGE_HOURS:
                    return FilterResult(
                        passed=False,
                        reason=f"Token too old: {age_hours:.0f} hours",
                        risk_score=0.1
                    )
            except (ValueError, TypeError):
                result.warnings.append("Invalid creation date")
                result.risk_score += 0.1
        
        # DEX filter
        dex_id = token_data.get('dexId', '').lower()
        if dex_id and dex_id not in self.trusted_dexs:
            result.warnings.append(f"Trading on untrusted DEX: {dex_id}")
            result.risk_score += 0.2
        
        return result
    
    def _check_trading_criteria(self, token_data: Dict[str, Any]) -> FilterResult:
        """Check trading-related criteria"""
        result = FilterResult(passed=True, warnings=[])
        
        # Transaction count filters
        txns = token_data.get('txns', {})
        
        # 5-minute transaction filter
        txns_5m = txns.get('m5', {})
        buys_5m = txns_5m.get('buys', 0)
        sells_5m = txns_5m.get('sells', 0)
        total_5m = buys_5m + sells_5m
        
        if total_5m < FILTER_CONFIG.MIN_TRANSACTIONS_5M:
            result.warnings.append(f"Low transaction count (5m): {total_5m}")
            result.risk_score += 0.2
        
        # Check for suspicious trading patterns
        if sells_5m > buys_5m * 3:  # Too many sells vs buys
            result.warnings.append("High sell pressure detected")
            result.risk_score += 0.3
        
        # Liquidity to volume ratio
        liquidity_usd = token_data.get('liquidity', {}).get('usd', 0)
        volume_5m = token_data.get('volume', {}).get('m5', 0)
        
        if volume_5m > 0 and liquidity_usd > 0:
            liquidity_ratio = liquidity_usd / volume_5m
            if liquidity_ratio < FILTER_CONFIG.MIN_LIQUIDITY_RATIO:
                result.warnings.append(f"Low liquidity ratio: {liquidity_ratio:.2f}")
                result.risk_score += 0.3
        
        return result
    
    def _assess_risk(self, token_data: Dict[str, Any]) -> FilterResult:
        """Assess overall risk based on various factors"""
        result = FilterResult(passed=True, warnings=[])
        
        base_token = token_data.get('baseToken', {})
        token_symbol = base_token.get('symbol', '')
        token_name = base_token.get('name', '')
        
        # Check for risky name patterns
        for pattern in self.risky_name_patterns:
            if pattern.search(token_name) or pattern.search(token_symbol):
                result.warnings.append(f"Suspicious name pattern detected")
                result.risk_score += 0.2
                break
        
        # Check for pump indicators
        for pattern in self.pump_patterns:
            if pattern.search(token_name) or pattern.search(token_symbol):
                result.warnings.append(f"Pump indicator detected in name/symbol")
                result.risk_score += 0.3
                break
        
        # Price change analysis
        price_change_5m = token_data.get('priceChange', {}).get('m5', 0)
        price_change_1h = token_data.get('priceChange', {}).get('h1', 0)
        price_change_24h = token_data.get('priceChange', {}).get('h24', 0)
        
        # Extreme price movements
        if abs(price_change_5m) > 100:  # >100% change in 5 minutes
            result.warnings.append(f"Extreme 5m price change: {price_change_5m:.1f}%")
            result.risk_score += 0.4
        
        if abs(price_change_1h) > 500:  # >500% change in 1 hour
            result.warnings.append(f"Extreme 1h price change: {price_change_1h:.1f}%")
            result.risk_score += 0.5
        
        # Volume spike detection
        volume_5m = token_data.get('volume', {}).get('m5', 0)
        volume_1h = token_data.get('volume', {}).get('h1', 0)
        
        if volume_1h > 0:
            volume_spike_ratio = (volume_5m * 12) / volume_1h  # Normalize to hourly
            if volume_spike_ratio > FILTER_CONFIG.VOLUME_SPIKE_THRESHOLD:
                result.warnings.append(f"Volume spike detected: {volume_spike_ratio:.1f}x")
                result.risk_score += 0.3
        
        return result
    
    async def _check_fake_volume(self, token_data: Dict[str, Any]) -> FilterResult:
        """Check for fake volume using Pocket Universe API and internal algorithms"""
        try:
            async with fake_volume_detector as detector:
                volume_analysis = await detector.analyze_volume(token_data)
                
                if volume_analysis.is_fake:
                    return FilterResult(
                        passed=False,
                        reason=f"Fake volume detected (confidence: {volume_analysis.confidence_score:.2f})",
                        risk_score=volume_analysis.confidence_score,
                        warnings=volume_analysis.reasons
                    )
                else:
                    # Even if not fake, add warnings for suspicious patterns
                    warnings = []
                    risk_score = 0.0
                    
                    if volume_analysis.wash_trading_score > 0.3:
                        warnings.append(f"Potential wash trading detected (score: {volume_analysis.wash_trading_score:.2f})")
                        risk_score += volume_analysis.wash_trading_score * 0.3
                    
                    if volume_analysis.volume_legitimacy_score < 0.7:
                        warnings.append(f"Low volume legitimacy score: {volume_analysis.volume_legitimacy_score:.2f}")
                        risk_score += (1.0 - volume_analysis.volume_legitimacy_score) * 0.2
                    
                    return FilterResult(
                        passed=True,
                        warnings=warnings,
                        risk_score=risk_score
                    )
                    
        except Exception as e:
            logger.error(f"Error during fake volume detection: {e}")
            return FilterResult(
                passed=True,
                warnings=["Fake volume detection failed"],
                risk_score=0.1
            )
    
    def add_to_blacklist(self, blacklist_type: str, address: str, reason: str = ""):
        """Add an address to the appropriate blacklist"""
        if blacklist_type.lower() == 'coin':
            self.coin_blacklist.add(address)
            logger.info(f"Added {address} to coin blacklist. Reason: {reason}")
        elif blacklist_type.lower() == 'dev':
            self.dev_blacklist.add(address)
            logger.info(f"Added {address} to dev blacklist. Reason: {reason}")
        else:
            raise ValueError(f"Invalid blacklist type: {blacklist_type}")
    
    def remove_from_blacklist(self, blacklist_type: str, address: str):
        """Remove an address from the appropriate blacklist"""
        if blacklist_type.lower() == 'coin':
            self.coin_blacklist.discard(address)
            logger.info(f"Removed {address} from coin blacklist")
        elif blacklist_type.lower() == 'dev':
            self.dev_blacklist.discard(address)
            logger.info(f"Removed {address} from dev blacklist")
        else:
            raise ValueError(f"Invalid blacklist type: {blacklist_type}")
    
    def is_blacklisted(self, blacklist_type: str, address: str) -> bool:
        """Check if an address is blacklisted"""
        if blacklist_type.lower() == 'coin':
            return address in self.coin_blacklist
        elif blacklist_type.lower() == 'dev':
            return address in self.dev_blacklist
        else:
            raise ValueError(f"Invalid blacklist type: {blacklist_type}")
    
    def get_blacklist_stats(self) -> Dict[str, int]:
        """Get statistics about blacklists"""
        return {
            'coin_blacklist_count': len(self.coin_blacklist),
            'dev_blacklist_count': len(self.dev_blacklist),
            'trusted_tokens_count': len(self.trusted_tokens),
            'trusted_dexs_count': len(self.trusted_dexs)
        }
    
    def export_blacklists(self) -> Dict[str, List[str]]:
        """Export blacklists for backup or sharing"""
        return {
            'coin_blacklist': list(self.coin_blacklist),
            'dev_blacklist': list(self.dev_blacklist),
            'trusted_tokens': list(self.trusted_tokens),
            'trusted_dexs': list(self.trusted_dexs)
        }
    
    def import_blacklists(self, blacklists_data: Dict[str, List[str]]):
        """Import blacklists from backup or external source"""
        if 'coin_blacklist' in blacklists_data:
            self.coin_blacklist.update(blacklists_data['coin_blacklist'])
        if 'dev_blacklist' in blacklists_data:
            self.dev_blacklist.update(blacklists_data['dev_blacklist'])
        if 'trusted_tokens' in blacklists_data:
            self.trusted_tokens.update(blacklists_data['trusted_tokens'])
        if 'trusted_dexs' in blacklists_data:
            self.trusted_dexs.update(blacklists_data['trusted_dexs'])
        
        logger.info("Blacklists imported successfully")

# Global filter manager instance
filter_manager = TokenFilterManager()