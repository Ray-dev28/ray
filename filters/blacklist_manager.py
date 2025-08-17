import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Set, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class BlacklistManager:
    """Manages persistent blacklists with file storage and automatic updates"""
    
    def __init__(self, blacklist_dir: str = "./blacklists"):
        self.blacklist_dir = Path(blacklist_dir)
        self.blacklist_dir.mkdir(exist_ok=True)
        
        # File paths
        self.coin_blacklist_file = self.blacklist_dir / "coin_blacklist.json"
        self.dev_blacklist_file = self.blacklist_dir / "dev_blacklist.json"
        self.trusted_tokens_file = self.blacklist_dir / "trusted_tokens.json"
        self.trusted_devs_file = self.blacklist_dir / "trusted_devs.json"
        self.auto_blacklist_file = self.blacklist_dir / "auto_blacklist.json"
        
        # In-memory sets
        self.coin_blacklist: Set[str] = set()
        self.dev_blacklist: Set[str] = set()
        self.trusted_tokens: Set[str] = set()
        self.trusted_devs: Set[str] = set()
        self.auto_blacklist: Dict[str, Dict] = {}  # Automatically detected scams
        
        # Load existing blacklists
        self._load_all_blacklists()
        
        logger.info(f"BlacklistManager initialized with {len(self.coin_blacklist)} coins and {len(self.dev_blacklist)} devs blacklisted")
    
    def _load_all_blacklists(self):
        """Load all blacklists from files"""
        self.coin_blacklist = self._load_set_from_file(self.coin_blacklist_file)
        self.dev_blacklist = self._load_set_from_file(self.dev_blacklist_file)
        self.trusted_tokens = self._load_set_from_file(self.trusted_tokens_file)
        self.trusted_devs = self._load_set_from_file(self.trusted_devs_file)
        self.auto_blacklist = self._load_dict_from_file(self.auto_blacklist_file)
    
    def _load_set_from_file(self, file_path: Path) -> Set[str]:
        """Load a set from JSON file"""
        try:
            if file_path.exists():
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    return set(data.get('items', []))
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
        return set()
    
    def _load_dict_from_file(self, file_path: Path) -> Dict:
        """Load a dictionary from JSON file"""
        try:
            if file_path.exists():
                with open(file_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
        return {}
    
    def _save_set_to_file(self, data: Set[str], file_path: Path, description: str):
        """Save a set to JSON file with metadata"""
        try:
            save_data = {
                'description': description,
                'last_updated': datetime.utcnow().isoformat(),
                'count': len(data),
                'items': sorted(list(data))
            }
            with open(file_path, 'w') as f:
                json.dump(save_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving {file_path}: {e}")
    
    def _save_dict_to_file(self, data: Dict, file_path: Path):
        """Save a dictionary to JSON file"""
        try:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving {file_path}: {e}")
    
    def add_coin_to_blacklist(self, token_address: str, reason: str = "", auto_detected: bool = False):
        """Add a token to the coin blacklist"""
        self.coin_blacklist.add(token_address)
        
        if auto_detected:
            self.auto_blacklist[token_address] = {
                'type': 'coin',
                'reason': reason,
                'detected_at': datetime.utcnow().isoformat(),
                'auto_detected': True
            }
            self._save_dict_to_file(self.auto_blacklist, self.auto_blacklist_file)
        
        self._save_set_to_file(
            self.coin_blacklist, 
            self.coin_blacklist_file, 
            "Blacklisted token addresses"
        )
        logger.info(f"Added token {token_address} to blacklist. Reason: {reason}")
    
    def add_dev_to_blacklist(self, dev_address: str, reason: str = "", auto_detected: bool = False):
        """Add a developer to the dev blacklist"""
        self.dev_blacklist.add(dev_address)
        
        if auto_detected:
            self.auto_blacklist[dev_address] = {
                'type': 'dev',
                'reason': reason,
                'detected_at': datetime.utcnow().isoformat(),
                'auto_detected': True
            }
            self._save_dict_to_file(self.auto_blacklist, self.auto_blacklist_file)
        
        self._save_set_to_file(
            self.dev_blacklist, 
            self.dev_blacklist_file, 
            "Blacklisted developer addresses"
        )
        logger.info(f"Added developer {dev_address} to blacklist. Reason: {reason}")
    
    def add_trusted_token(self, token_address: str):
        """Add a token to the trusted list"""
        self.trusted_tokens.add(token_address)
        self._save_set_to_file(
            self.trusted_tokens, 
            self.trusted_tokens_file, 
            "Trusted token addresses"
        )
        logger.info(f"Added token {token_address} to trusted list")
    
    def add_trusted_dev(self, dev_address: str):
        """Add a developer to the trusted list"""
        self.trusted_devs.add(dev_address)
        self._save_set_to_file(
            self.trusted_devs, 
            self.trusted_devs_file, 
            "Trusted developer addresses"
        )
        logger.info(f"Added developer {dev_address} to trusted list")
    
    def remove_from_coin_blacklist(self, token_address: str):
        """Remove a token from the blacklist"""
        self.coin_blacklist.discard(token_address)
        if token_address in self.auto_blacklist:
            del self.auto_blacklist[token_address]
            self._save_dict_to_file(self.auto_blacklist, self.auto_blacklist_file)
        
        self._save_set_to_file(
            self.coin_blacklist, 
            self.coin_blacklist_file, 
            "Blacklisted token addresses"
        )
        logger.info(f"Removed token {token_address} from blacklist")
    
    def remove_from_dev_blacklist(self, dev_address: str):
        """Remove a developer from the blacklist"""
        self.dev_blacklist.discard(dev_address)
        if dev_address in self.auto_blacklist:
            del self.auto_blacklist[dev_address]
            self._save_dict_to_file(self.auto_blacklist, self.auto_blacklist_file)
        
        self._save_set_to_file(
            self.dev_blacklist, 
            self.dev_blacklist_file, 
            "Blacklisted developer addresses"
        )
        logger.info(f"Removed developer {dev_address} from blacklist")
    
    def is_coin_blacklisted(self, token_address: str) -> bool:
        """Check if a token is blacklisted"""
        return token_address in self.coin_blacklist
    
    def is_dev_blacklisted(self, dev_address: str) -> bool:
        """Check if a developer is blacklisted"""
        return dev_address in self.dev_blacklist
    
    def is_token_trusted(self, token_address: str) -> bool:
        """Check if a token is trusted"""
        return token_address in self.trusted_tokens
    
    def is_dev_trusted(self, dev_address: str) -> bool:
        """Check if a developer is trusted"""
        return dev_address in self.trusted_devs
    
    def get_blacklist_reason(self, address: str) -> Optional[str]:
        """Get the reason for blacklisting an address"""
        if address in self.auto_blacklist:
            return self.auto_blacklist[address].get('reason', 'Unknown')
        return None
    
    def get_stats(self) -> Dict[str, int]:
        """Get blacklist statistics"""
        return {
            'coin_blacklist_count': len(self.coin_blacklist),
            'dev_blacklist_count': len(self.dev_blacklist),
            'trusted_tokens_count': len(self.trusted_tokens),
            'trusted_devs_count': len(self.trusted_devs),
            'auto_detected_count': len(self.auto_blacklist)
        }
    
    def export_all_blacklists(self) -> Dict[str, List[str]]:
        """Export all blacklists for backup"""
        return {
            'coin_blacklist': list(self.coin_blacklist),
            'dev_blacklist': list(self.dev_blacklist),
            'trusted_tokens': list(self.trusted_tokens),
            'trusted_devs': list(self.trusted_devs),
            'auto_blacklist': self.auto_blacklist
        }
    
    def import_blacklists(self, data: Dict[str, List[str]]):
        """Import blacklists from external source"""
        if 'coin_blacklist' in data:
            self.coin_blacklist.update(data['coin_blacklist'])
            self._save_set_to_file(
                self.coin_blacklist, 
                self.coin_blacklist_file, 
                "Blacklisted token addresses"
            )
        
        if 'dev_blacklist' in data:
            self.dev_blacklist.update(data['dev_blacklist'])
            self._save_set_to_file(
                self.dev_blacklist, 
                self.dev_blacklist_file, 
                "Blacklisted developer addresses"
            )
        
        if 'trusted_tokens' in data:
            self.trusted_tokens.update(data['trusted_tokens'])
            self._save_set_to_file(
                self.trusted_tokens, 
                self.trusted_tokens_file, 
                "Trusted token addresses"
            )
        
        if 'trusted_devs' in data:
            self.trusted_devs.update(data['trusted_devs'])
            self._save_set_to_file(
                self.trusted_devs, 
                self.trusted_devs_file, 
                "Trusted developer addresses"
            )
        
        if 'auto_blacklist' in data:
            self.auto_blacklist.update(data['auto_blacklist'])
            self._save_dict_to_file(self.auto_blacklist, self.auto_blacklist_file)
        
        logger.info("Blacklists imported successfully")
    
    def cleanup_old_entries(self, days_old: int = 30):
        """Remove old auto-detected entries that haven't been confirmed"""
        from datetime import timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        to_remove = []
        
        for address, data in self.auto_blacklist.items():
            if data.get('auto_detected', False):
                detected_at = datetime.fromisoformat(data['detected_at'])
                if detected_at < cutoff_date:
                    to_remove.append(address)
        
        for address in to_remove:
            # Remove from auto blacklist but keep in main blacklist if manually confirmed
            del self.auto_blacklist[address]
        
        if to_remove:
            self._save_dict_to_file(self.auto_blacklist, self.auto_blacklist_file)
            logger.info(f"Cleaned up {len(to_remove)} old auto-detected entries")
    
    def get_recent_additions(self, hours: int = 24) -> Dict[str, List[Dict]]:
        """Get recently added blacklist entries"""
        from datetime import timedelta
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        recent_coins = []
        recent_devs = []
        
        for address, data in self.auto_blacklist.items():
            detected_at = datetime.fromisoformat(data['detected_at'])
            if detected_at > cutoff_time:
                entry = {
                    'address': address,
                    'reason': data['reason'],
                    'detected_at': data['detected_at'],
                    'auto_detected': data.get('auto_detected', False)
                }
                
                if data['type'] == 'coin':
                    recent_coins.append(entry)
                elif data['type'] == 'dev':
                    recent_devs.append(entry)
        
        return {
            'coins': recent_coins,
            'devs': recent_devs
        }

# Global blacklist manager instance
blacklist_manager = BlacklistManager()