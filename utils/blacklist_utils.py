#!/usr/bin/env python3
"""
Blacklist Management Utilities

This module provides utility functions for managing coin and developer blacklists,
including automatic detection and manual management.
"""

import json
import logging
import asyncio
from typing import Dict, List, Set, Optional, Tuple
from datetime import datetime
from pathlib import Path

from filters.blacklist_manager import blacklist_manager
from filters.filter_manager import filter_manager
from filters.fake_volume_detector import fake_volume_detector

logger = logging.getLogger(__name__)

class BlacklistUtils:
    """Utility functions for blacklist management"""
    
    @staticmethod
    def add_coin_to_blacklist(token_address: str, reason: str = "", auto_detected: bool = False) -> bool:
        """Add a coin to the blacklist"""
        try:
            blacklist_manager.add_coin_to_blacklist(token_address, reason, auto_detected)
            logger.info(f"Successfully added {token_address} to coin blacklist")
            return True
        except Exception as e:
            logger.error(f"Failed to add {token_address} to coin blacklist: {e}")
            return False
    
    @staticmethod
    def add_dev_to_blacklist(dev_address: str, reason: str = "", auto_detected: bool = False) -> bool:
        """Add a developer to the blacklist"""
        try:
            blacklist_manager.add_dev_to_blacklist(dev_address, reason, auto_detected)
            logger.info(f"Successfully added {dev_address} to dev blacklist")
            return True
        except Exception as e:
            logger.error(f"Failed to add {dev_address} to dev blacklist: {e}")
            return False
    
    @staticmethod
    def remove_coin_from_blacklist(token_address: str) -> bool:
        """Remove a coin from the blacklist"""
        try:
            blacklist_manager.remove_from_coin_blacklist(token_address)
            logger.info(f"Successfully removed {token_address} from coin blacklist")
            return True
        except Exception as e:
            logger.error(f"Failed to remove {token_address} from coin blacklist: {e}")
            return False
    
    @staticmethod
    def remove_dev_from_blacklist(dev_address: str) -> bool:
        """Remove a developer from the blacklist"""
        try:
            blacklist_manager.remove_from_dev_blacklist(dev_address)
            logger.info(f"Successfully removed {dev_address} from dev blacklist")
            return True
        except Exception as e:
            logger.error(f"Failed to remove {dev_address} from dev blacklist: {e}")
            return False
    
    @staticmethod
    async def analyze_and_blacklist_if_fake_volume(token_data: Dict) -> Tuple[bool, str]:
        """Analyze token for fake volume and blacklist if detected"""
        try:
            async with fake_volume_detector as detector:
                analysis = await detector.analyze_volume(token_data)
                
                if analysis.is_fake and analysis.confidence_score > 0.7:
                    token_address = token_data.get('baseToken', {}).get('address', '')
                    token_symbol = token_data.get('baseToken', {}).get('symbol', 'Unknown')
                    
                    if token_address:
                        reason = f"Fake volume detected (confidence: {analysis.confidence_score:.2f}). Reasons: {', '.join(analysis.reasons[:3])}"
                        
                        success = BlacklistUtils.add_coin_to_blacklist(
                            token_address, 
                            reason, 
                            auto_detected=True
                        )
                        
                        if success:
                            return True, f"Token {token_symbol} blacklisted for fake volume"
                        else:
                            return False, f"Failed to blacklist {token_symbol}"
                    else:
                        return False, "No token address available"
                else:
                    return False, f"Token passed fake volume check (confidence: {analysis.confidence_score:.2f})"
                    
        except Exception as e:
            logger.error(f"Error analyzing token for fake volume: {e}")
            return False, f"Analysis failed: {str(e)}"
    
    @staticmethod
    def bulk_analyze_tokens(token_list: List[Dict]) -> Dict[str, List]:
        """Analyze multiple tokens and categorize them"""
        results = {
            'blacklisted': [],
            'suspicious': [],
            'clean': [],
            'errors': []
        }
        
        async def analyze_batch(tokens):
            tasks = []
            for token in tokens:
                task = BlacklistUtils.analyze_and_blacklist_if_fake_volume(token)
                tasks.append(task)
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, result in enumerate(batch_results):
                token = tokens[i]
                token_symbol = token.get('baseToken', {}).get('symbol', 'Unknown')
                
                if isinstance(result, Exception):
                    results['errors'].append({
                        'token': token_symbol,
                        'error': str(result)
                    })
                else:
                    blacklisted, message = result
                    if blacklisted:
                        results['blacklisted'].append({
                            'token': token_symbol,
                            'reason': message
                        })
                    elif 'suspicious' in message.lower():
                        results['suspicious'].append({
                            'token': token_symbol,
                            'message': message
                        })
                    else:
                        results['clean'].append({
                            'token': token_symbol,
                            'message': message
                        })
        
        # Run the async analysis
        asyncio.run(analyze_batch(token_list))
        return results
    
    @staticmethod
    def export_blacklists_to_file(output_path: str = "./blacklists_export.json") -> bool:
        """Export all blacklists to a JSON file"""
        try:
            blacklists = blacklist_manager.export_all_blacklists()
            
            export_data = {
                'export_timestamp': datetime.utcnow().isoformat(),
                'blacklists': blacklists,
                'stats': blacklist_manager.get_stats()
            }
            
            with open(output_path, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            logger.info(f"Blacklists exported to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export blacklists: {e}")
            return False
    
    @staticmethod
    def import_blacklists_from_file(input_path: str) -> bool:
        """Import blacklists from a JSON file"""
        try:
            with open(input_path, 'r') as f:
                data = json.load(f)
            
            if 'blacklists' in data:
                blacklist_manager.import_blacklists(data['blacklists'])
                logger.info(f"Blacklists imported from {input_path}")
                return True
            else:
                logger.error("Invalid blacklist file format")
                return False
                
        except Exception as e:
            logger.error(f"Failed to import blacklists: {e}")
            return False
    
    @staticmethod
    def get_blacklist_summary() -> Dict:
        """Get a comprehensive summary of all blacklists"""
        stats = blacklist_manager.get_stats()
        recent_additions = blacklist_manager.get_recent_additions(24)  # Last 24 hours
        
        return {
            'statistics': stats,
            'recent_additions': recent_additions,
            'filter_stats': filter_manager.get_blacklist_stats()
        }
    
    @staticmethod
    def cleanup_old_auto_detections(days_old: int = 30) -> int:
        """Clean up old auto-detected entries"""
        try:
            blacklist_manager.cleanup_old_entries(days_old)
            logger.info(f"Cleaned up auto-detections older than {days_old} days")
            return days_old
        except Exception as e:
            logger.error(f"Failed to cleanup old entries: {e}")
            return 0
    
    @staticmethod
    def validate_blacklist_integrity() -> Dict[str, List[str]]:
        """Validate blacklist integrity and find potential issues"""
        issues = {
            'invalid_addresses': [],
            'duplicates': [],
            'conflicting_entries': []
        }
        
        # Check for invalid Solana addresses (should be 32-44 characters)
        for address in blacklist_manager.coin_blacklist:
            if len(address) < 32 or len(address) > 44:
                issues['invalid_addresses'].append(f"Invalid coin address: {address}")
        
        for address in blacklist_manager.dev_blacklist:
            if len(address) < 32 or len(address) > 44:
                issues['invalid_addresses'].append(f"Invalid dev address: {address}")
        
        # Check for conflicts between blacklist and trusted lists
        coin_conflicts = blacklist_manager.coin_blacklist.intersection(blacklist_manager.trusted_tokens)
        dev_conflicts = blacklist_manager.dev_blacklist.intersection(blacklist_manager.trusted_devs)
        
        for address in coin_conflicts:
            issues['conflicting_entries'].append(f"Token {address} is both blacklisted and trusted")
        
        for address in dev_conflicts:
            issues['conflicting_entries'].append(f"Developer {address} is both blacklisted and trusted")
        
        return issues

def main():
    """Main function for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Blacklist Management Utilities")
    parser.add_argument('--export', type=str, help="Export blacklists to file")
    parser.add_argument('--import', type=str, dest='import_file', help="Import blacklists from file")
    parser.add_argument('--summary', action='store_true', help="Show blacklist summary")
    parser.add_argument('--cleanup', type=int, help="Cleanup auto-detections older than N days")
    parser.add_argument('--validate', action='store_true', help="Validate blacklist integrity")
    parser.add_argument('--add-coin', type=str, help="Add coin to blacklist")
    parser.add_argument('--add-dev', type=str, help="Add developer to blacklist")
    parser.add_argument('--reason', type=str, help="Reason for blacklisting")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    if args.export:
        success = BlacklistUtils.export_blacklists_to_file(args.export)
        print(f"Export {'successful' if success else 'failed'}")
    
    elif args.import_file:
        success = BlacklistUtils.import_blacklists_from_file(args.import_file)
        print(f"Import {'successful' if success else 'failed'}")
    
    elif args.summary:
        summary = BlacklistUtils.get_blacklist_summary()
        print(json.dumps(summary, indent=2))
    
    elif args.cleanup:
        cleaned = BlacklistUtils.cleanup_old_auto_detections(args.cleanup)
        print(f"Cleaned up entries older than {cleaned} days")
    
    elif args.validate:
        issues = BlacklistUtils.validate_blacklist_integrity()
        if any(issues.values()):
            print("Blacklist integrity issues found:")
            print(json.dumps(issues, indent=2))
        else:
            print("No blacklist integrity issues found")
    
    elif args.add_coin:
        reason = args.reason or "Manual addition"
        success = BlacklistUtils.add_coin_to_blacklist(args.add_coin, reason)
        print(f"Adding coin {'successful' if success else 'failed'}")
    
    elif args.add_dev:
        reason = args.reason or "Manual addition"
        success = BlacklistUtils.add_dev_to_blacklist(args.add_dev, reason)
        print(f"Adding developer {'successful' if success else 'failed'}")
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()