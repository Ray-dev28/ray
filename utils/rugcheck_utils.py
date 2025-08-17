#!/usr/bin/env python3
"""
RugCheck Utility Functions

This module provides utility functions for RugCheck.xyz integration,
including contract verification, bundle detection, and batch analysis.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

from filters.rugcheck_analyzer import rugcheck_analyzer, RugCheckResult
from filters.blacklist_manager import blacklist_manager
from config import RUGCHECK_CONFIG

logger = logging.getLogger(__name__)

class RugCheckUtils:
    """Utility functions for RugCheck operations"""
    
    @staticmethod
    async def verify_token_contract(token_address: str, chain: str = "solana") -> Tuple[bool, str, Dict]:
        """Verify a single token contract using RugCheck"""
        try:
            async with rugcheck_analyzer as analyzer:
                result = await analyzer.analyze_token(token_address, chain)
                
                is_safe = result.is_good_contract and not result.is_bundled
                
                if not result.is_good_contract:
                    message = f"Contract not marked as 'Good' (status: {result.status})"
                elif result.is_bundled:
                    message = f"Token supply is bundled ({result.bundle_percentage:.1f}%)"
                else:
                    message = "Contract verified as safe"
                
                details = {
                    'status': result.status,
                    'is_good': result.is_good_contract,
                    'is_bundled': result.is_bundled,
                    'bundle_percentage': result.bundle_percentage,
                    'risk_score': result.risk_score,
                    'reasons': result.reasons,
                    'security': {
                        'mint_authority_disabled': result.mint_authority_disabled,
                        'freeze_authority_disabled': result.freeze_authority_disabled,
                        'liquidity_locked': result.liquidity_locked
                    }
                }
                
                return is_safe, message, details
                
        except Exception as e:
            logger.error(f"Error verifying token {token_address}: {e}")
            return False, f"Verification failed: {str(e)}", {}
    
    @staticmethod
    async def batch_verify_tokens(token_addresses: List[str], chain: str = "solana") -> Dict[str, Dict]:
        """Verify multiple tokens in batch"""
        results = {}
        
        try:
            async with rugcheck_analyzer as analyzer:
                analysis_results = await analyzer.bulk_analyze_tokens(token_addresses, chain)
                
                for address, result in analysis_results.items():
                    is_safe = result.is_good_contract and not result.is_bundled
                    
                    if not result.is_good_contract:
                        message = f"Contract not marked as 'Good' (status: {result.status})"
                    elif result.is_bundled:
                        message = f"Token supply is bundled ({result.bundle_percentage:.1f}%)"
                    else:
                        message = "Contract verified as safe"
                    
                    results[address] = {
                        'is_safe': is_safe,
                        'message': message,
                        'status': result.status,
                        'is_good': result.is_good_contract,
                        'is_bundled': result.is_bundled,
                        'bundle_percentage': result.bundle_percentage,
                        'risk_score': result.risk_score,
                        'reasons': result.reasons
                    }
        
        except Exception as e:
            logger.error(f"Error in batch verification: {e}")
            for address in token_addresses:
                results[address] = {
                    'is_safe': False,
                    'message': f"Verification failed: {str(e)}",
                    'error': True
                }
        
        return results
    
    @staticmethod
    async def detect_and_blacklist_bundles(token_addresses: List[str], chain: str = "solana") -> Dict[str, List]:
        """Detect bundled tokens and add them to blacklist"""
        results = {
            'bundled': [],
            'not_good': [],
            'safe': [],
            'errors': []
        }
        
        try:
            verification_results = await RugCheckUtils.batch_verify_tokens(token_addresses, chain)
            
            for address, result in verification_results.items():
                if result.get('error'):
                    results['errors'].append({
                        'address': address,
                        'message': result['message']
                    })
                elif result.get('is_bundled'):
                    # Add bundled token to blacklist
                    reason = f"Bundled token supply ({result['bundle_percentage']:.1f}% held by top holder)"
                    success = blacklist_manager.add_coin_to_blacklist(
                        address, 
                        reason, 
                        auto_detected=True
                    )
                    
                    results['bundled'].append({
                        'address': address,
                        'bundle_percentage': result['bundle_percentage'],
                        'blacklisted': success,
                        'reason': reason
                    })
                elif not result.get('is_good'):
                    # Add non-good contracts to blacklist
                    reason = f"Contract not marked as 'Good' by RugCheck (status: {result['status']})"
                    success = blacklist_manager.add_coin_to_blacklist(
                        address, 
                        reason, 
                        auto_detected=True
                    )
                    
                    results['not_good'].append({
                        'address': address,
                        'status': result['status'],
                        'blacklisted': success,
                        'reason': reason
                    })
                else:
                    results['safe'].append({
                        'address': address,
                        'status': result['status'],
                        'risk_score': result['risk_score']
                    })
        
        except Exception as e:
            logger.error(f"Error detecting bundles: {e}")
            for address in token_addresses:
                results['errors'].append({
                    'address': address,
                    'message': f"Detection failed: {str(e)}"
                })
        
        return results
    
    @staticmethod
    async def analyze_token_security(token_address: str, chain: str = "solana") -> Dict[str, Any]:
        """Comprehensive security analysis of a token"""
        try:
            async with rugcheck_analyzer as analyzer:
                result = await analyzer.analyze_token(token_address, chain)
                
                security_analysis = {
                    'overall_status': result.status,
                    'is_safe': result.is_good_contract and not result.is_bundled,
                    'risk_score': result.risk_score,
                    'contract_verification': {
                        'is_good_contract': result.is_good_contract,
                        'status': result.status
                    },
                    'supply_analysis': {
                        'is_bundled': result.is_bundled,
                        'bundle_percentage': result.bundle_percentage,
                        'top_holders': result.top_holders[:5]  # Top 5 holders
                    },
                    'security_features': {
                        'mint_authority_disabled': result.mint_authority_disabled,
                        'freeze_authority_disabled': result.freeze_authority_disabled,
                        'liquidity_locked': result.liquidity_locked
                    },
                    'risk_factors': result.reasons,
                    'recommendations': []
                }
                
                # Generate recommendations
                if not result.is_good_contract:
                    security_analysis['recommendations'].append("❌ Avoid this token - contract not verified as safe")
                
                if result.is_bundled:
                    security_analysis['recommendations'].append(f"❌ Avoid this token - {result.bundle_percentage:.1f}% supply held by single address")
                
                if not result.mint_authority_disabled:
                    security_analysis['recommendations'].append("⚠️  Mint authority not disabled - new tokens can be created")
                
                if not result.freeze_authority_disabled:
                    security_analysis['recommendations'].append("⚠️  Freeze authority not disabled - accounts can be frozen")
                
                if not result.liquidity_locked:
                    security_analysis['recommendations'].append("⚠️  Liquidity not locked - can be removed by developers")
                
                if result.bundle_percentage > 20:
                    security_analysis['recommendations'].append(f"⚠️  High holder concentration ({result.bundle_percentage:.1f}%)")
                
                if not security_analysis['recommendations']:
                    security_analysis['recommendations'].append("✅ Token appears to have good security characteristics")
                
                return security_analysis
                
        except Exception as e:
            logger.error(f"Error analyzing token security: {e}")
            return {
                'overall_status': 'error',
                'is_safe': False,
                'error': str(e),
                'recommendations': ["❌ Unable to analyze token security"]
            }
    
    @staticmethod
    def export_rugcheck_results(results: Dict, output_path: str = "./rugcheck_results.json") -> bool:
        """Export RugCheck analysis results to JSON file"""
        try:
            export_data = {
                'export_timestamp': datetime.utcnow().isoformat(),
                'rugcheck_config': {
                    'bundle_threshold': RUGCHECK_CONFIG.BUNDLE_DETECTION_THRESHOLD,
                    'only_good_contracts': RUGCHECK_CONFIG.ONLY_GOOD_CONTRACTS
                },
                'results': results
            }
            
            with open(output_path, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            logger.info(f"RugCheck results exported to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export RugCheck results: {e}")
            return False
    
    @staticmethod
    async def monitor_new_tokens(token_addresses: List[str], auto_blacklist: bool = True) -> Dict[str, Any]:
        """Monitor new tokens and automatically blacklist problematic ones"""
        monitoring_results = {
            'total_analyzed': len(token_addresses),
            'safe_tokens': 0,
            'blacklisted_tokens': 0,
            'failed_analysis': 0,
            'details': []
        }
        
        try:
            batch_results = await RugCheckUtils.batch_verify_tokens(token_addresses)
            
            for address, result in batch_results.items():
                detail = {
                    'address': address,
                    'is_safe': result.get('is_safe', False),
                    'status': result.get('status', 'unknown'),
                    'action_taken': 'none'
                }
                
                if result.get('error'):
                    monitoring_results['failed_analysis'] += 1
                    detail['action_taken'] = 'analysis_failed'
                
                elif not result.get('is_safe') and auto_blacklist:
                    # Automatically blacklist problematic tokens
                    reason = result.get('message', 'Failed RugCheck verification')
                    success = blacklist_manager.add_coin_to_blacklist(
                        address, 
                        reason, 
                        auto_detected=True
                    )
                    
                    if success:
                        monitoring_results['blacklisted_tokens'] += 1
                        detail['action_taken'] = 'blacklisted'
                        detail['blacklist_reason'] = reason
                
                else:
                    monitoring_results['safe_tokens'] += 1
                    detail['action_taken'] = 'approved'
                
                monitoring_results['details'].append(detail)
        
        except Exception as e:
            logger.error(f"Error monitoring tokens: {e}")
            monitoring_results['error'] = str(e)
        
        return monitoring_results
    
    @staticmethod
    def get_rugcheck_stats() -> Dict[str, Any]:
        """Get RugCheck analyzer statistics"""
        try:
            cache_stats = rugcheck_analyzer.get_cache_stats()
            
            return {
                'rugcheck_config': {
                    'enabled': RUGCHECK_CONFIG.ENABLE_RUGCHECK,
                    'only_good_contracts': RUGCHECK_CONFIG.ONLY_GOOD_CONTRACTS,
                    'bundle_threshold': RUGCHECK_CONFIG.BUNDLE_DETECTION_THRESHOLD,
                    'cache_duration': RUGCHECK_CONFIG.CACHE_DURATION
                },
                'cache_stats': cache_stats,
                'api_info': {
                    'base_url': RUGCHECK_CONFIG.API_BASE_URL,
                    'timeout': RUGCHECK_CONFIG.API_TIMEOUT
                }
            }
        
        except Exception as e:
            logger.error(f"Error getting RugCheck stats: {e}")
            return {'error': str(e)}

def main():
    """Main function for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description="RugCheck Utility Functions")
    parser.add_argument('--verify', type=str, help="Verify single token contract")
    parser.add_argument('--batch-verify', type=str, help="Batch verify tokens from file (one address per line)")
    parser.add_argument('--detect-bundles', type=str, help="Detect and blacklist bundled tokens from file")
    parser.add_argument('--analyze-security', type=str, help="Comprehensive security analysis of token")
    parser.add_argument('--export', type=str, help="Export results to file")
    parser.add_argument('--stats', action='store_true', help="Show RugCheck statistics")
    parser.add_argument('--chain', type=str, default='solana', help="Blockchain to analyze (default: solana)")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    async def run_async_command():
        if args.verify:
            is_safe, message, details = await RugCheckUtils.verify_token_contract(args.verify, args.chain)
            print(f"Token: {args.verify}")
            print(f"Safe: {is_safe}")
            print(f"Message: {message}")
            print(f"Details: {json.dumps(details, indent=2)}")
            
            if args.export:
                RugCheckUtils.export_rugcheck_results({args.verify: details}, args.export)
        
        elif args.batch_verify:
            try:
                with open(args.batch_verify, 'r') as f:
                    addresses = [line.strip() for line in f if line.strip()]
                
                results = await RugCheckUtils.batch_verify_tokens(addresses, args.chain)
                
                print(f"Batch verification results for {len(addresses)} tokens:")
                for address, result in results.items():
                    print(f"  {address}: {'✅ Safe' if result['is_safe'] else '❌ Unsafe'} - {result['message']}")
                
                if args.export:
                    RugCheckUtils.export_rugcheck_results(results, args.export)
            
            except FileNotFoundError:
                print(f"File not found: {args.batch_verify}")
        
        elif args.detect_bundles:
            try:
                with open(args.detect_bundles, 'r') as f:
                    addresses = [line.strip() for line in f if line.strip()]
                
                results = await RugCheckUtils.detect_and_blacklist_bundles(addresses, args.chain)
                
                print(f"Bundle detection results:")
                print(f"  Bundled tokens: {len(results['bundled'])}")
                print(f"  Non-good contracts: {len(results['not_good'])}")
                print(f"  Safe tokens: {len(results['safe'])}")
                print(f"  Errors: {len(results['errors'])}")
                
                if args.export:
                    RugCheckUtils.export_rugcheck_results(results, args.export)
            
            except FileNotFoundError:
                print(f"File not found: {args.detect_bundles}")
        
        elif args.analyze_security:
            analysis = await RugCheckUtils.analyze_token_security(args.analyze_security, args.chain)
            
            print(f"Security Analysis for {args.analyze_security}:")
            print(json.dumps(analysis, indent=2))
            
            if args.export:
                RugCheckUtils.export_rugcheck_results({args.analyze_security: analysis}, args.export)
    
    if args.stats:
        stats = RugCheckUtils.get_rugcheck_stats()
        print("RugCheck Statistics:")
        print(json.dumps(stats, indent=2))
    
    elif any([args.verify, args.batch_verify, args.detect_bundles, args.analyze_security]):
        asyncio.run(run_async_command())
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()