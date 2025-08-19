# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from run_backtest import BacktestEngine
import json
from datetime import datetime

class StrategyOptimizer:
    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self.df = pd.read_csv(csv_path)
        self.best_params = None
        self.optimization_results = []
        
    @staticmethod
    def generate_sample_data(periods: int = 1000) -> pd.DataFrame:
        dates = pd.date_range(start='2024-01-01', periods=periods, freq='5min')
        
        np.random.seed(42)
        price = 50000
        prices = []
        volumes = []
        
        for i in range(periods):
            trend = np.sin(i / 100) * 0.002
            noise = np.random.randn() * 0.005
            price *= (1 + trend + noise)
            prices.append(price)
            
            vol_base = 1000000
            vol_noise = np.random.exponential(0.5) * vol_base
            volumes.append(vol_base + vol_noise)
        
        df = pd.DataFrame({
            'date': dates,
            'open': prices,
            'high': [p * (1 + np.random.uniform(0, 0.01)) for p in prices],
            'low': [p * (1 - np.random.uniform(0, 0.01)) for p in prices],
            'close': prices,
            'volume': volumes
        })
        
        return df
    
    def test_fee_sensitivity(self) -> Dict:
        fee_rates = [0.0001, 0.0002, 0.0005, 0.001, 0.002]
        results = {}
        
        for fee in fee_rates:
            engine = BacktestEngine(initial_krw=1_000_000, fee_rate=fee)
            metrics = engine.run(self.df)
            results[fee] = {
                'return': metrics['total_return_pct'],
                'sharpe': metrics['sharpe_ratio'],
                'trades': metrics['total_trades']
            }
        
        return results
    
    def optimize_position_sizes(self) -> Dict:
        base_sizes = {
            0: [0.03, 0.05, 0.07],
            1: [0.08, 0.10, 0.12],
            2: [0.06, 0.08, 0.10],
            3: [0.06, 0.08, 0.10],
            4: [0.08, 0.10, 0.12],
            5: [0.10, 0.12, 0.15],
            6: [0.12, 0.15, 0.18],
            7: [0.12, 0.15, 0.18],
            8: [0.15, 0.20, 0.25],
            9: [0.03, 0.05, 0.07]
        }
        
        best_config = None
        best_return = -float('inf')
        
        for stage, sizes in base_sizes.items():
            for size in sizes:
                engine = BacktestEngine(initial_krw=1_000_000)
                metrics = engine.run(self.df)
                
                if metrics['total_return_pct'] > best_return:
                    best_return = metrics['total_return_pct']
                    best_config = {'stage': stage, 'size': size, 'metrics': metrics}
        
        return best_config
    
    def analyze_market_conditions(self) -> Dict:
        from strategy_engine import calc_market_snapshot, calc_market_index
        
        snapshots = []
        indices = []
        
        for i in range(60, len(self.df)):
            window = self.df.iloc[:i+1]
            snap = calc_market_snapshot(window)
            idx = calc_market_index(snap)
            
            snapshots.append({
                'rsi': snap.rsi,
                'volume_rel': snap.volume_rel_5d,
                'bb_width': snap.bb_width,
                'momentum': np.mean([snap.close_changes_1d, 
                                    snap.close_changes_3d, 
                                    snap.close_changes_7d])
            })
            indices.append(idx)
        
        stage_distribution = pd.Series(indices).value_counts().to_dict()
        
        avg_metrics = pd.DataFrame(snapshots).mean().to_dict()
        
        return {
            'stage_distribution': stage_distribution,
            'average_metrics': avg_metrics,
            'volatility_periods': sum(1 for s in snapshots if s['bb_width'] > 0.05),
            'high_volume_periods': sum(1 for s in snapshots if s['volume_rel'] > 1.5)
        }
    
    def run_comprehensive_test(self) -> Dict:
        print("\n" + "="*60)
        print("STRATEGY OPTIMIZATION & TESTING SUITE")
        print("="*60)
        
        print("\n1. Running base backtest...")
        base_engine = BacktestEngine(initial_krw=1_000_000, fee_rate=0.0005)
        base_results = base_engine.run(self.df)
        
        print(f"   Base Return: {base_results['total_return_pct']:.2f}%")
        print(f"   Sharpe Ratio: {base_results['sharpe_ratio']:.2f}")
        print(f"   Win Rate: {base_results['win_rate_pct']:.2f}%")
        
        print("\n2. Testing fee sensitivity...")
        fee_results = self.test_fee_sensitivity()
        optimal_fee = min(fee_results.keys(), 
                         key=lambda f: -fee_results[f]['return'])
        print(f"   Optimal fee consideration: {optimal_fee*100:.03f}%")
        
        print("\n3. Analyzing market conditions...")
        market_analysis = self.analyze_market_conditions()
        print(f"   High volatility periods: {market_analysis['volatility_periods']}")
        print(f"   High volume periods: {market_analysis['high_volume_periods']}")
        
        print("\n4. Stage distribution:")
        for stage, count in sorted(market_analysis['stage_distribution'].items()):
            pct = count / sum(market_analysis['stage_distribution'].values()) * 100
            print(f"   Stage {stage}: {count} periods ({pct:.1f}%)")
        
        return {
            'base_results': base_results,
            'fee_analysis': fee_results,
            'market_analysis': market_analysis,
            'timestamp': datetime.now().isoformat()
        }
    
    def save_optimization_report(self, results: Dict, filename: str = 'optimization_report.json'):
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\nOptimization report saved to {filename}")

def validate_strategy_logic():
    print("\n" + "="*60)
    print("STRATEGY VALIDATION TEST")
    print("="*60)
    
    from strategy_engine import (
        calc_market_snapshot, 
        calc_market_index,
        STRATEGY_MAP
    )
    
    optimizer = StrategyOptimizer('dummy.csv')
    test_df = optimizer.generate_sample_data(500)
    
    print("\n1. Testing market index calculation...")
    indices = []
    for i in range(60, 100):
        window = test_df.iloc[:i+1]
        snap = calc_market_snapshot(window)
        idx = calc_market_index(snap)
        indices.append(idx)
    
    print(f"   Index range: {min(indices)} - {max(indices)}")
    print(f"   Average index: {np.mean(indices):.2f}")
    
    print("\n2. Testing strategy mapping...")
    strategies_triggered = set()
    for i in range(60, 100):
        window = test_df.iloc[:i+1]
        snap = calc_market_snapshot(window)
        idx = calc_market_index(snap)
        strat = STRATEGY_MAP.get(idx)
        if strat:
            plan = strat(window, snap)
            if plan:
                strategies_triggered.add(idx)
    
    print(f"   Strategies triggered: {sorted(strategies_triggered)}")
    
    print("\n3. Testing risk management...")
    from strategy_engine import RiskManager
    
    risk_mgr = RiskManager()
    test_trades = [
        {'pnl': 5000},
        {'pnl': -3000},
        {'pnl': 2000},
        {'pnl': -8000},
        {'pnl': 4000}
    ]
    
    for trade in test_trades:
        risk_mgr.update_pnl(trade['pnl'])
    
    print(f"   Daily PnL: {risk_mgr.daily_pnl:,.0f} KRW")
    print(f"   Trades today: {risk_mgr.trades_today}")
    
    balance = 1_000_000
    if risk_mgr.daily_pnl < -balance * risk_mgr.daily_loss_limit_pct:
        print("   ⚠️ Daily loss limit reached!")
    else:
        print("   ✅ Within daily loss limit")
    
    print("\nValidation complete!")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
        print(f"Optimizing strategy with data from: {csv_file}")
        
        optimizer = StrategyOptimizer(csv_file)
        results = optimizer.run_comprehensive_test()
        optimizer.save_optimization_report(results)
    else:
        print("Running validation tests...")
        validate_strategy_logic()
        
        print("\n" + "="*60)
        print("To run optimization with your data:")
        print("python test_optimizer.py your_data.csv")
        print("="*60)