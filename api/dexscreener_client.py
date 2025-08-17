import asyncio
import aiohttp
import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime

from config import API_CONFIG, SOLANA_CONFIG

logger = logging.getLogger(__name__)

class DexScreenerClient:
    """Client for interacting with DexScreener API"""
    
    def __init__(self):
        self.base_url = API_CONFIG.BASE_URL
        self.session = None
        self.last_request_time = 0
        self.request_count = 0
        
        logger.info("DexScreenerClient initialized")
    
    async def __aenter__(self):
        """Async context manager entry"""
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
        timeout = aiohttp.ClientTimeout(total=API_CONFIG.REQUEST_TIMEOUT)
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'User-Agent': 'SolanaTokenBot/1.0',
                'Accept': 'application/json'
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def _rate_limit(self):
        """Implement rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < API_CONFIG.RATE_LIMIT_DELAY:
            wait_time = API_CONFIG.RATE_LIMIT_DELAY - time_since_last
            await asyncio.sleep(wait_time)
        
        self.last_request_time = time.time()
        self.request_count += 1
    
    async def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make HTTP request with error handling and retries"""
        if not self.session:
            logger.error("Session not initialized")
            return None
        
        await self._rate_limit()
        
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(API_CONFIG.MAX_RETRIES):
            try:
                async with self.session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.debug(f"Successful request to {endpoint}")
                        return data
                    elif response.status == 429:
                        # Rate limited, wait longer
                        wait_time = 2 ** attempt
                        logger.warning(f"Rate limited, waiting {wait_time}s before retry")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        logger.warning(f"Request failed with status {response.status}")
                        return None
                        
            except asyncio.TimeoutError:
                logger.warning(f"Request timeout for {endpoint} (attempt {attempt + 1})")
                if attempt < API_CONFIG.MAX_RETRIES - 1:
                    await asyncio.sleep(1)
                    continue
            except Exception as e:
                logger.error(f"Request error for {endpoint}: {e}")
                if attempt < API_CONFIG.MAX_RETRIES - 1:
                    await asyncio.sleep(1)
                    continue
        
        logger.error(f"All retry attempts failed for {endpoint}")
        return None
    
    async def get_tokens_by_chain(self, chain: str = "solana", limit: int = 50) -> Optional[List[Dict]]:
        """Get tokens by blockchain"""
        try:
            endpoint = f"/dex/tokens/{chain}"
            params = {"limit": limit}
            
            data = await self._make_request(endpoint, params)
            if data and 'pairs' in data:
                return data['pairs']
            
            return []
            
        except Exception as e:
            logger.error(f"Error fetching tokens by chain: {e}")
            return None
    
    async def get_token_pairs(self, token_address: str) -> Optional[List[Dict]]:
        """Get all pairs for a specific token"""
        try:
            endpoint = f"/dex/tokens/{token_address}"
            
            data = await self._make_request(endpoint)
            if data and 'pairs' in data:
                return data['pairs']
            
            return []
            
        except Exception as e:
            logger.error(f"Error fetching token pairs for {token_address}: {e}")
            return None
    
    async def get_pair_info(self, pair_address: str) -> Optional[Dict]:
        """Get information about a specific pair"""
        try:
            endpoint = f"/dex/pairs/{pair_address}"
            
            data = await self._make_request(endpoint)
            if data and 'pair' in data:
                return data['pair']
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching pair info for {pair_address}: {e}")
            return None
    
    async def search_tokens(self, query: str) -> Optional[List[Dict]]:
        """Search for tokens by name or symbol"""
        try:
            endpoint = "/dex/search"
            params = {"q": query}
            
            data = await self._make_request(endpoint, params)
            if data and 'pairs' in data:
                return data['pairs']
            
            return []
            
        except Exception as e:
            logger.error(f"Error searching tokens with query '{query}': {e}")
            return None
    
    async def get_trending_tokens(self, chain: str = "solana") -> Optional[List[Dict]]:
        """Get trending tokens for a specific chain"""
        try:
            # DexScreener doesn't have a specific trending endpoint
            # We'll get recent tokens and sort by volume
            endpoint = f"/dex/tokens/{chain}"
            params = {"limit": 100}
            
            data = await self._make_request(endpoint, params)
            if data and 'pairs' in data:
                pairs = data['pairs']
                
                # Filter and sort by 24h volume
                solana_pairs = [
                    pair for pair in pairs 
                    if pair.get('chainId') == 'solana'
                ]
                
                # Sort by volume (descending)
                trending = sorted(
                    solana_pairs,
                    key=lambda x: x.get('volume', {}).get('h24', 0),
                    reverse=True
                )
                
                return trending[:20]  # Top 20 trending
            
            return []
            
        except Exception as e:
            logger.error(f"Error fetching trending tokens: {e}")
            return None
    
    async def get_new_pairs(self, hours: int = 24) -> Optional[List[Dict]]:
        """Get new pairs created within specified hours"""
        try:
            # Get recent tokens and filter by creation time
            endpoint = "/dex/tokens/solana"
            params = {"limit": 200}
            
            data = await self._make_request(endpoint, params)
            if not data or 'pairs' not in data:
                return []
            
            current_time = datetime.utcnow()
            cutoff_time = current_time.timestamp() - (hours * 3600)
            
            new_pairs = []
            for pair in data['pairs']:
                pair_created_at = pair.get('pairCreatedAt')
                if pair_created_at and pair_created_at / 1000 > cutoff_time:
                    new_pairs.append(pair)
            
            # Sort by creation time (newest first)
            new_pairs.sort(
                key=lambda x: x.get('pairCreatedAt', 0),
                reverse=True
            )
            
            return new_pairs
            
        except Exception as e:
            logger.error(f"Error fetching new pairs: {e}")
            return None
    
    async def filter_solana_tokens(self, pairs: List[Dict]) -> List[Dict]:
        """Filter pairs to only include Solana tokens meeting criteria"""
        if not pairs:
            return []
        
        filtered_pairs = []
        
        for pair in pairs:
            try:
                # Check if it's a Solana pair
                if pair.get('chainId') != 'solana':
                    continue
                
                # Check minimum liquidity
                liquidity_usd = pair.get('liquidity', {}).get('usd', 0)
                if liquidity_usd < SOLANA_CONFIG.MIN_LIQUIDITY_USD:
                    continue
                
                # Check minimum volume
                volume_24h = pair.get('volume', {}).get('h24', 0)
                if volume_24h < SOLANA_CONFIG.MIN_VOLUME_24H_USD:
                    continue
                
                # Check if base token exists
                base_token = pair.get('baseToken')
                if not base_token or not base_token.get('address'):
                    continue
                
                filtered_pairs.append(pair)
                
            except Exception as e:
                logger.warning(f"Error filtering pair: {e}")
                continue
        
        return filtered_pairs
    
    async def get_token_analytics(self, token_address: str) -> Optional[Dict]:
        """Get comprehensive analytics for a token"""
        try:
            pairs = await self.get_token_pairs(token_address)
            if not pairs:
                return None
            
            # Find the main pair (highest liquidity)
            main_pair = max(pairs, key=lambda x: x.get('liquidity', {}).get('usd', 0))
            
            # Calculate analytics
            analytics = {
                'token_address': token_address,
                'symbol': main_pair.get('baseToken', {}).get('symbol', ''),
                'name': main_pair.get('baseToken', {}).get('name', ''),
                'price_usd': main_pair.get('priceUsd', 0),
                'total_pairs': len(pairs),
                'total_liquidity': sum(pair.get('liquidity', {}).get('usd', 0) for pair in pairs),
                'total_volume_24h': sum(pair.get('volume', {}).get('h24', 0) for pair in pairs),
                'main_pair': main_pair,
                'all_pairs': pairs,
                'analytics_timestamp': datetime.utcnow().isoformat()
            }
            
            return analytics
            
        except Exception as e:
            logger.error(f"Error getting token analytics: {e}")
            return None
    
    def get_request_stats(self) -> Dict[str, Any]:
        """Get API request statistics"""
        return {
            'total_requests': self.request_count,
            'base_url': self.base_url,
            'rate_limit_delay': API_CONFIG.RATE_LIMIT_DELAY,
            'max_retries': API_CONFIG.MAX_RETRIES,
            'timeout': API_CONFIG.REQUEST_TIMEOUT
        }

# Global client instance
dexscreener_client = DexScreenerClient()