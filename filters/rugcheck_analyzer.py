import asyncio
import aiohttp
import logging
import time
import os
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from dataclasses import dataclass

from config import RUGCHECK_CONFIG

logger = logging.getLogger(__name__)

@dataclass
class RugCheckResult:
    """Result of RugCheck analysis"""
    is_good_contract: bool
    is_bundled: bool
    risk_score: float
    status: str
    reasons: List[str]
    bundle_percentage: float = 0.0
    top_holders: List[Dict] = None
    liquidity_locked: bool = False
    mint_authority_disabled: bool = False
    freeze_authority_disabled: bool = False
    
    def __post_init__(self):
        if self.top_holders is None:
            self.top_holders = []
        if self.reasons is None:
            self.reasons = []

class RugCheckAnalyzer:
    """Analyzes tokens using RugCheck.xyz API for contract verification and bundle detection"""
    
    def __init__(self):
        self.api_key = os.getenv('RUGCHECK_API_KEY')
        self.session = None
        self.cache = {}  # Simple in-memory cache
        self.cache_expiry = {}
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.5  # 500ms between requests
        
        logger.info("RugCheckAnalyzer initialized")
    
    async def __aenter__(self):
        """Async context manager entry"""
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
        timeout = aiohttp.ClientTimeout(total=RUGCHECK_CONFIG.API_TIMEOUT)
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'User-Agent': 'SolanaTokenBot/1.0',
                'Accept': 'application/json'
            }
        )
        
        if self.api_key:
            self.session.headers.update({'X-API-KEY': self.api_key})
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def analyze_token(self, token_address: str, chain: str = "solana") -> RugCheckResult:
        """Comprehensive token analysis using RugCheck.xyz"""
        
        if not token_address:
            return RugCheckResult(
                is_good_contract=False,
                is_bundled=False,
                risk_score=1.0,
                status="error",
                reasons=["No token address provided"]
            )
        
        # Check cache first
        cache_key = f"rugcheck_{chain}_{token_address}"
        if self._is_cached(cache_key):
            return self.cache[cache_key]
        
        try:
            # Rate limiting
            await self._rate_limit()
            
            # Make API request
            analysis_data = await self._make_rugcheck_request(token_address, chain)
            
            if not analysis_data:
                result = RugCheckResult(
                    is_good_contract=False,
                    is_bundled=False,
                    risk_score=0.8,
                    status="api_error",
                    reasons=["Failed to fetch data from RugCheck API"]
                )
            else:
                result = self._parse_rugcheck_response(analysis_data)
            
            # Cache the result
            self._cache_result(cache_key, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing token {token_address} with RugCheck: {e}")
            return RugCheckResult(
                is_good_contract=False,
                is_bundled=False,
                risk_score=0.9,
                status="error",
                reasons=[f"Analysis failed: {str(e)}"]
            )
    
    async def _make_rugcheck_request(self, token_address: str, chain: str) -> Optional[Dict]:
        """Make request to RugCheck API"""
        if not self.session:
            return None
        
        try:
            url = f"{RUGCHECK_CONFIG.API_BASE_URL}{RUGCHECK_CONFIG.TOKEN_SCAN_ENDPOINT}/{chain}/{token_address}"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 429:
                    logger.warning("RugCheck API rate limit exceeded")
                    await asyncio.sleep(2)  # Wait before retry
                    return None
                elif response.status == 404:
                    logger.warning(f"Token {token_address} not found on RugCheck")
                    return None
                else:
                    logger.warning(f"RugCheck API returned status {response.status}")
                    return None
                    
        except asyncio.TimeoutError:
            logger.warning("RugCheck API request timeout")
            return None
        except Exception as e:
            logger.error(f"Error making RugCheck API request: {e}")
            return None
    
    def _parse_rugcheck_response(self, data: Dict[str, Any]) -> RugCheckResult:
        """Parse RugCheck API response"""
        
        # Extract basic information
        status = data.get('result', '').lower()
        is_good_contract = status == 'good'
        
        risks = data.get('risks', [])
        reasons = [risk.get('description', '') for risk in risks if risk.get('description')]
        
        # Calculate risk score based on status and risks
        risk_score = self._calculate_risk_score(status, risks)
        
        # Analyze holder distribution for bundling
        holder_analysis = data.get('holderAnalysis', {})
        top_holders = holder_analysis.get('topHolders', [])
        
        is_bundled, bundle_percentage = self._detect_bundling(top_holders)
        
        # Extract security features
        security = data.get('security', {})
        mint_authority_disabled = security.get('mintAuthorityDisabled', False)
        freeze_authority_disabled = security.get('freezeAuthorityDisabled', False)
        
        # Extract liquidity information
        liquidity_info = data.get('liquidity', {})
        liquidity_locked = liquidity_info.get('locked', False)
        
        # Add bundle-related reasons
        if is_bundled:
            reasons.append(f"Token supply is bundled ({bundle_percentage:.1f}% held by top holder)")
        
        # Add security-related reasons
        if not mint_authority_disabled:
            reasons.append("Mint authority not disabled - tokens can be minted")
        
        if not freeze_authority_disabled:
            reasons.append("Freeze authority not disabled - accounts can be frozen")
        
        if not liquidity_locked:
            reasons.append("Liquidity not locked - can be removed")
        
        return RugCheckResult(
            is_good_contract=is_good_contract,
            is_bundled=is_bundled,
            risk_score=risk_score,
            status=status,
            reasons=reasons,
            bundle_percentage=bundle_percentage,
            top_holders=top_holders,
            liquidity_locked=liquidity_locked,
            mint_authority_disabled=mint_authority_disabled,
            freeze_authority_disabled=freeze_authority_disabled
        )
    
    def _calculate_risk_score(self, status: str, risks: List[Dict]) -> float:
        """Calculate risk score based on status and identified risks"""
        base_scores = {
            'good': 0.1,
            'warning': 0.4,
            'danger': 0.8,
            'critical': 0.95,
            'unknown': 0.5
        }
        
        base_score = base_scores.get(status.lower(), 0.5)
        
        # Add risk points based on specific risks
        risk_points = 0.0
        for risk in risks:
            risk_level = risk.get('level', '').lower()
            if risk_level == 'high':
                risk_points += 0.2
            elif risk_level == 'medium':
                risk_points += 0.1
            elif risk_level == 'low':
                risk_points += 0.05
        
        # Cap the total risk score at 1.0
        return min(base_score + risk_points, 1.0)
    
    def _detect_bundling(self, top_holders: List[Dict]) -> Tuple[bool, float]:
        """Detect if token supply is bundled based on holder distribution"""
        if not top_holders:
            return False, 0.0
        
        # Get the top holder's percentage
        top_holder = top_holders[0]
        top_percentage = top_holder.get('percentage', 0.0)
        
        # Check if it exceeds the bundle threshold
        is_bundled = top_percentage >= RUGCHECK_CONFIG.BUNDLE_DETECTION_THRESHOLD
        
        return is_bundled, top_percentage
    
    async def bulk_analyze_tokens(self, token_addresses: List[str], chain: str = "solana") -> Dict[str, RugCheckResult]:
        """Analyze multiple tokens concurrently"""
        
        # Create tasks for concurrent analysis
        tasks = []
        for address in token_addresses:
            task = self.analyze_token(address, chain)
            tasks.append(task)
        
        # Execute tasks with proper error handling
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        analysis_results = {}
        for i, result in enumerate(results):
            address = token_addresses[i]
            if isinstance(result, Exception):
                analysis_results[address] = RugCheckResult(
                    is_good_contract=False,
                    is_bundled=False,
                    risk_score=1.0,
                    status="error",
                    reasons=[f"Analysis failed: {str(result)}"]
                )
            else:
                analysis_results[address] = result
        
        return analysis_results
    
    async def _rate_limit(self):
        """Implement rate limiting for API requests"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.min_request_interval:
            wait_time = self.min_request_interval - time_since_last_request
            await asyncio.sleep(wait_time)
        
        self.last_request_time = time.time()
    
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
    
    def _cache_result(self, cache_key: str, result: RugCheckResult):
        """Cache analysis result"""
        self.cache[cache_key] = result
        self.cache_expiry[cache_key] = time.time() + RUGCHECK_CONFIG.CACHE_DURATION
        
        # Simple cache cleanup - remove oldest entries if cache gets too large
        if len(self.cache) > 1000:
            oldest_key = min(self.cache_expiry.keys(), key=lambda k: self.cache_expiry[k])
            del self.cache[oldest_key]
            del self.cache_expiry[oldest_key]
    
    def clear_cache(self):
        """Clear all cached results"""
        self.cache.clear()
        self.cache_expiry.clear()
        logger.info("RugCheck analysis cache cleared")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        return {
            'cached_entries': len(self.cache),
            'expired_entries': sum(1 for k, v in self.cache_expiry.items() if time.time() > v)
        }

# Global RugCheck analyzer instance
rugcheck_analyzer = RugCheckAnalyzer()