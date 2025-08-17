import asyncio
import aiohttp
import logging
import time
import statistics
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import json
import os

from config import POCKET_UNIVERSE_CONFIG, FILTER_CONFIG

logger = logging.getLogger(__name__)

@dataclass
class VolumeAnalysisResult:
    """Result of volume analysis"""
    is_fake: bool
    confidence_score: float
    reasons: List[str]
    wash_trading_score: float = 0.0
    volume_legitimacy_score: float = 0.0
    source: str = "internal"
    
class FakeVolumeDetector:
    """Detects fake volume using multiple algorithms including Pocket Universe API"""
    
    def __init__(self):
        self.pocket_universe_api_key = os.getenv('POCKET_UNIVERSE_API_KEY')
        self.session = None
        self.cache = {}  # Simple in-memory cache
        self.cache_expiry = {}
        
        # Volume analysis thresholds
        self.volume_spike_threshold = 10.0  # 10x normal volume
        self.wash_trading_threshold = 0.6
        self.legitimate_volume_threshold = 0.3
        
        logger.info("FakeVolumeDetector initialized")
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=POCKET_UNIVERSE_CONFIG.API_TIMEOUT)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def analyze_volume(self, token_data: Dict[str, Any]) -> VolumeAnalysisResult:
        """Comprehensive volume analysis using multiple methods"""
        token_address = token_data.get('baseToken', {}).get('address', '')
        
        if not token_address:
            return VolumeAnalysisResult(
                is_fake=False,
                confidence_score=0.0,
                reasons=["No token address provided"]
            )
        
        # Check cache first
        cache_key = f"volume_analysis_{token_address}"
        if self._is_cached(cache_key):
            return self.cache[cache_key]
        
        results = []
        
        # 1. Pocket Universe API analysis (if available)
        if POCKET_UNIVERSE_CONFIG.ENABLE_POCKET_UNIVERSE and self.pocket_universe_api_key:
            pu_result = await self._pocket_universe_analysis(token_address, token_data)
            if pu_result:
                results.append(pu_result)
        
        # 2. Internal volume pattern analysis
        internal_result = self._internal_volume_analysis(token_data)
        results.append(internal_result)
        
        # 3. Wash trading detection
        wash_result = self._detect_wash_trading(token_data)
        results.append(wash_result)
        
        # 4. Volume-price correlation analysis
        correlation_result = self._analyze_volume_price_correlation(token_data)
        results.append(correlation_result)
        
        # Combine results
        final_result = self._combine_analysis_results(results)
        
        # Cache the result
        self._cache_result(cache_key, final_result)
        
        return final_result
    
    async def _pocket_universe_analysis(self, token_address: str, token_data: Dict[str, Any]) -> Optional[VolumeAnalysisResult]:
        """Analyze volume using Pocket Universe API"""
        if not self.session:
            return None
        
        try:
            # Volume verification endpoint
            url = f"{POCKET_UNIVERSE_CONFIG.API_BASE_URL}{POCKET_UNIVERSE_CONFIG.VOLUME_CHECK_ENDPOINT}"
            headers = {
                'Authorization': f'Bearer {self.pocket_universe_api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'token_address': token_address,
                'chain': 'solana',
                'timeframe': '24h'
            }
            
            async with self.session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_pocket_universe_response(data)
                else:
                    logger.warning(f"Pocket Universe API returned status {response.status}")
                    
        except asyncio.TimeoutError:
            logger.warning("Pocket Universe API timeout")
        except Exception as e:
            logger.error(f"Error calling Pocket Universe API: {e}")
        
        return None
    
    def _parse_pocket_universe_response(self, data: Dict[str, Any]) -> VolumeAnalysisResult:
        """Parse Pocket Universe API response"""
        is_fake = data.get('is_fake_volume', False)
        confidence = data.get('confidence_score', 0.0)
        wash_trading_score = data.get('wash_trading_score', 0.0)
        legitimacy_score = data.get('volume_legitimacy_score', 1.0)
        
        reasons = []
        if is_fake:
            reasons.extend(data.get('red_flags', []))
        
        return VolumeAnalysisResult(
            is_fake=is_fake,
            confidence_score=confidence,
            reasons=reasons,
            wash_trading_score=wash_trading_score,
            volume_legitimacy_score=legitimacy_score,
            source="pocket_universe"
        )
    
    def _internal_volume_analysis(self, token_data: Dict[str, Any]) -> VolumeAnalysisResult:
        """Internal volume pattern analysis"""
        reasons = []
        is_fake = False
        confidence = 0.0
        
        volume_data = token_data.get('volume', {})
        volume_5m = volume_data.get('m5', 0)
        volume_1h = volume_data.get('h1', 0)
        volume_6h = volume_data.get('h6', 0)
        volume_24h = volume_data.get('h24', 0)
        
        # Check for volume consistency
        if volume_24h > 0:
            # Expected hourly volume based on 24h
            expected_hourly = volume_24h / 24
            
            # Check if recent volume is suspiciously high
            if volume_1h > expected_hourly * self.volume_spike_threshold:
                reasons.append(f"Suspicious volume spike: {volume_1h/expected_hourly:.1f}x normal")
                confidence += 0.3
                is_fake = True
            
            # Check volume progression consistency
            volume_ratios = []
            if volume_5m > 0:
                volume_ratios.append(volume_1h / (volume_5m * 12))  # Normalize 5m to hourly
            if volume_1h > 0:
                volume_ratios.append(volume_6h / (volume_1h * 6))   # Normalize 1h to 6h
            if volume_6h > 0:
                volume_ratios.append(volume_24h / (volume_6h * 4))  # Normalize 6h to 24h
            
            # Check for inconsistent volume patterns
            if len(volume_ratios) > 1:
                ratio_variance = statistics.variance(volume_ratios) if len(volume_ratios) > 1 else 0
                if ratio_variance > 2.0:  # High variance indicates inconsistent patterns
                    reasons.append(f"Inconsistent volume pattern detected (variance: {ratio_variance:.2f})")
                    confidence += 0.2
        
        # Check transaction count vs volume
        txns = token_data.get('txns', {})
        txns_24h_total = txns.get('h24', {}).get('buys', 0) + txns.get('h24', {}).get('sells', 0)
        
        if txns_24h_total > 0 and volume_24h > 0:
            avg_volume_per_txn = volume_24h / txns_24h_total
            
            # Suspiciously high volume per transaction
            if avg_volume_per_txn > 50000:  # $50k per transaction on average
                reasons.append(f"High volume per transaction: ${avg_volume_per_txn:,.0f}")
                confidence += 0.25
                is_fake = True
        
        return VolumeAnalysisResult(
            is_fake=is_fake,
            confidence_score=min(confidence, 1.0),
            reasons=reasons,
            source="internal"
        )
    
    def _detect_wash_trading(self, token_data: Dict[str, Any]) -> VolumeAnalysisResult:
        """Detect wash trading patterns"""
        reasons = []
        wash_score = 0.0
        
        txns = token_data.get('txns', {})
        
        # Analyze different timeframes
        for timeframe in ['m5', 'h1', 'h6', 'h24']:
            txn_data = txns.get(timeframe, {})
            buys = txn_data.get('buys', 0)
            sells = txn_data.get('sells', 0)
            
            if buys + sells > 0:
                # Check for perfect or near-perfect buy/sell balance
                balance_ratio = min(buys, sells) / max(buys, sells) if max(buys, sells) > 0 else 0
                
                if balance_ratio > 0.9:  # Very balanced trading
                    reasons.append(f"Suspicious buy/sell balance in {timeframe}: {balance_ratio:.2f}")
                    wash_score += 0.2
                
                # Check for round number transactions
                if buys % 10 == 0 and sells % 10 == 0 and (buys + sells) > 20:
                    reasons.append(f"Round number transactions in {timeframe}")
                    wash_score += 0.1
        
        # Check volume vs liquidity ratio
        volume_24h = token_data.get('volume', {}).get('h24', 0)
        liquidity_usd = token_data.get('liquidity', {}).get('usd', 0)
        
        if liquidity_usd > 0 and volume_24h > 0:
            volume_to_liquidity_ratio = volume_24h / liquidity_usd
            
            # Extremely high volume compared to liquidity might indicate wash trading
            if volume_to_liquidity_ratio > 50:  # 50x daily volume vs liquidity
                reasons.append(f"Extreme volume/liquidity ratio: {volume_to_liquidity_ratio:.1f}x")
                wash_score += 0.3
        
        is_fake = wash_score > self.wash_trading_threshold
        
        return VolumeAnalysisResult(
            is_fake=is_fake,
            confidence_score=min(wash_score, 1.0),
            reasons=reasons,
            wash_trading_score=wash_score,
            source="wash_trading_detection"
        )
    
    def _analyze_volume_price_correlation(self, token_data: Dict[str, Any]) -> VolumeAnalysisResult:
        """Analyze volume-price correlation for anomalies"""
        reasons = []
        correlation_score = 0.0
        
        # Get price changes and volumes
        price_changes = token_data.get('priceChange', {})
        volumes = token_data.get('volume', {})
        
        # Check if high volume correlates with minimal price movement
        volume_24h = volumes.get('h24', 0)
        price_change_24h = abs(price_changes.get('h24', 0))
        
        if volume_24h > 100000 and price_change_24h < 5:  # High volume, low price movement
            reasons.append(f"High volume (${volume_24h:,.0f}) with minimal price movement ({price_change_24h:.1f}%)")
            correlation_score += 0.3
        
        # Check for volume spikes without corresponding price impact
        volume_1h = volumes.get('h1', 0)
        price_change_1h = abs(price_changes.get('h1', 0))
        
        if volume_1h > 50000 and price_change_1h < 2:  # Volume spike without price impact
            reasons.append(f"Volume spike without price impact in 1h")
            correlation_score += 0.2
        
        is_fake = correlation_score > 0.4
        
        return VolumeAnalysisResult(
            is_fake=is_fake,
            confidence_score=correlation_score,
            reasons=reasons,
            source="volume_price_correlation"
        )
    
    def _combine_analysis_results(self, results: List[VolumeAnalysisResult]) -> VolumeAnalysisResult:
        """Combine multiple analysis results into a final verdict"""
        if not results:
            return VolumeAnalysisResult(is_fake=False, confidence_score=0.0, reasons=["No analysis performed"])
        
        # Weight different sources
        source_weights = {
            "pocket_universe": 0.4,
            "internal": 0.25,
            "wash_trading_detection": 0.25,
            "volume_price_correlation": 0.1
        }
        
        weighted_confidence = 0.0
        total_weight = 0.0
        all_reasons = []
        max_wash_score = 0.0
        min_legitimacy_score = 1.0
        
        fake_votes = 0
        total_votes = 0
        
        for result in results:
            weight = source_weights.get(result.source, 0.1)
            weighted_confidence += result.confidence_score * weight
            total_weight += weight
            all_reasons.extend(result.reasons)
            
            max_wash_score = max(max_wash_score, result.wash_trading_score)
            min_legitimacy_score = min(min_legitimacy_score, result.volume_legitimacy_score)
            
            if result.is_fake:
                fake_votes += 1
            total_votes += 1
        
        # Calculate final confidence
        final_confidence = weighted_confidence / total_weight if total_weight > 0 else 0.0
        
        # Determine if fake based on threshold and voting
        is_fake = (
            final_confidence > FILTER_CONFIG.FAKE_VOLUME_THRESHOLD or
            fake_votes >= (total_votes * 0.6)  # Majority vote
        )
        
        return VolumeAnalysisResult(
            is_fake=is_fake,
            confidence_score=final_confidence,
            reasons=all_reasons,
            wash_trading_score=max_wash_score,
            volume_legitimacy_score=min_legitimacy_score,
            source="combined"
        )
    
    def _is_cached(self, cache_key: str) -> bool:
        """Check if result is cached and not expired"""
        if cache_key not in self.cache:
            return False
        
        if cache_key in self.cache_expiry:
            if time.time() > self.cache_expiry[cache_key]:
                del self.cache[cache_key]
                del self.cache_expiry[cache_key]
                return False
        
        return True
    
    def _cache_result(self, cache_key: str, result: VolumeAnalysisResult):
        """Cache analysis result"""
        self.cache[cache_key] = result
        self.cache_expiry[cache_key] = time.time() + POCKET_UNIVERSE_CONFIG.CACHE_DURATION
        
        # Simple cache cleanup - remove oldest entries if cache gets too large
        if len(self.cache) > 1000:
            oldest_key = min(self.cache_expiry.keys(), key=lambda k: self.cache_expiry[k])
            del self.cache[oldest_key]
            del self.cache_expiry[oldest_key]
    
    def clear_cache(self):
        """Clear all cached results"""
        self.cache.clear()
        self.cache_expiry.clear()
        logger.info("Volume analysis cache cleared")

# Global fake volume detector instance
fake_volume_detector = FakeVolumeDetector()