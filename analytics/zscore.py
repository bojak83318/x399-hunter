#!/usr/bin/env python3
"""
Pricing anomaly detector using Z-score on Git history.
Reads all JSON files in data/, calculates statistics, flags deals.
"""
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta
import statistics

def load_historical_data(data_dir: str, lookback_days: int):
    """
    Loads all JSON snapshots from data_dir within lookback window.
    Returns: List of all items with prices.
    """
    cutoff = datetime.utcnow() - timedelta(days=lookback_days)
    all_items = []
    
    # Walk through all tool subdirectories
    for json_file in Path(data_dir).rglob('*.json'):
        try:
            # Filename format: YYYY-MM-DD_HH-MM.json
            ts_str = json_file.stem
            file_time = datetime.strptime(ts_str, '%Y-%m-%d_%H-%M')
            
            if file_time < cutoff:
                continue
            
            with open(json_file) as f:
                items = json.load(f)
                all_items.extend(items)
        except Exception:
            # Skip files that don't match pattern
            continue
    
    return all_items

def calculate_zscore(items: list, current_price: float):
    if len(items) < 3:
        return 0.0
    
    prices = [item['price_sgd'] for item in items if 'price_sgd' in item and item['price_sgd'] > 0]
    
    if not prices:
        return 0.0
    
    mu = statistics.mean(prices)
    sigma = statistics.stdev(prices) if len(prices) > 1 else 1.0
    
    if sigma == 0:
        return 0.0
        
    return (current_price - mu) / sigma

def analyze_deals(data_dir: str, lookback_days: int, z_threshold: float = -1.5):
    historical = load_historical_data(data_dir, lookback_days)
    
    # Get latest snapshot per source
    sources = ['carousell', 'ebay', 'slickdeals']
    deals = []
    
    for source in sources:
        source_dir = Path(data_dir) / source
        if not source_dir.exists():
            continue
            
        json_files = list(source_dir.glob('*.json'))
        if not json_files:
            continue
            
        latest_file = max(json_files, key=lambda p: p.stat().st_mtime)
        try:
            with open(latest_file) as f:
                current_items = json.load(f)
        except:
            continue
            
        for item in current_items:
            if 'price_sgd' not in item or item['price_sgd'] <= 0:
                continue
            
            # Filter historical to same source/item type roughly if possible
            # For MVP, we use global Z-score for simplicity, or source-specific
            # Ideally we match by title similarity, but for now global distribution per source
            
            # Filter history by source
            source_history = [h for h in historical if h.get('source') == source]
            
            z = calculate_zscore(source_history, item['price_sgd'])
            
            if z < z_threshold:
                item['z_score'] = round(z, 2)
                item['flag'] = '🔥 GREAT DEAL'
                deals.append(item)
    
    return deals

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-dir', required=True)
    parser.add_argument('--lookback-days', type=int, default=30)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    
    deals = analyze_deals(args.data_dir, args.lookback_days)
    
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, 'w') as f:
        json.dump(deals, f, indent=2)
    
    print(f"✅ Found {len(deals)} deals -> {args.output}")
    
import os
if __name__ == "__main__":
    main()
