# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict, Tuple
from strategy_engine import decide_order, RiskManager
import json

class BacktestEngine:
    def __init__(self, initial_krw: float = 1_000_000, fee_rate: float = 0.0005):
        self.initial_krw = initial_krw
        self.fee_rate = fee_rate
        self.cash = initial_krw
        self.positions = []
        self.trades = []
        self.equity_curve = []
        self.market_states = []
        self.risk_manager = RiskManager()
        
    def calculate_fees(self, amount: float) -> float:
        return amount * self.fee_rate
    
    def execute_buy(self, price: float, qty: float, tp: float, sl: float, note: str, timestamp):
        cost = qty * price
        fee = self.calculate_fees(cost)
        total_cost = cost + fee
        
        if total_cost <= self.cash:
            self.cash -= total_cost
            self.positions.append({
                'qty': qty,
                'entry_price': price,
                'tp': tp,
                'sl': sl,
                'note': note,
                'entry_time': timestamp,
                'entry_fee': fee
            })
            self.trades.append({
                'time': timestamp,
                'type': 'BUY',
                'price': price,
                'qty': qty,
                'fee': fee,
                'note': note
            })
            return True
        return False
    
    def check_exits(self, high: float, low: float, close: float, timestamp):
        closed_positions = []
        remaining_positions = []
        
        for pos in self.positions:
            if pos['tp'] and high >= pos['tp']:
                exit_price = pos['tp']
                exit_type = 'TP'
            elif pos['sl'] and low <= pos['sl']:
                exit_price = pos['sl']
                exit_type = 'SL'
            else:
                remaining_positions.append(pos)
                continue
            
            revenue = pos['qty'] * exit_price
            fee = self.calculate_fees(revenue)
            net_revenue = revenue - fee
            self.cash += net_revenue
            
            pnl = net_revenue - (pos['qty'] * pos['entry_price'] + pos['entry_fee'])
            pnl_pct = (pnl / (pos['qty'] * pos['entry_price'])) * 100
            
            self.risk_manager.update_pnl(pnl)
            
            self.trades.append({
                'time': timestamp,
                'type': exit_type,
                'price': exit_price,
                'qty': pos['qty'],
                'fee': fee,
                'pnl': pnl,
                'pnl_pct': pnl_pct,
                'note': pos['note']
            })
            closed_positions.append(pos)
        
        self.positions = remaining_positions
        return closed_positions
    
    def get_total_value(self, current_price: float) -> float:
        position_value = sum(pos['qty'] * current_price for pos in self.positions)
        return self.cash + position_value
    
    def run(self, df: pd.DataFrame, lookback: int = 60) -> Dict:
        df = df.copy()
        df.columns = [c.lower() for c in df.columns]
        
        if 'timestamp' not in df.columns and 'date' in df.columns:
            df['timestamp'] = pd.to_datetime(df['date'])
        elif 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        for i in range(lookback, len(df)):
            window = df.iloc[:i+1].copy()
            current = df.iloc[i]
            timestamp = current.get('timestamp', i)
            
            if i % 288 == 0:
                self.risk_manager.reset_daily()
            
            closed = self.check_exits(
                current['high'], 
                current['low'], 
                current['close'],
                timestamp
            )
            
            total_value = self.get_total_value(current['close'])
            
            result = decide_order(window, self.cash, self.risk_manager)
            self.market_states.append({
                'time': timestamp,
                'index': result['index'],
                'stage': result['stage_name'],
                'rsi': result['snapshot']['rsi'],
                'volume_rel': result['snapshot']['volume_rel_5d']
            })
            
            if result['plan'] and self.cash > 5500:
                plan = result['plan']
                success = self.execute_buy(
                    current['close'],
                    plan['qty'],
                    plan['tp'],
                    plan['sl'],
                    plan['note'],
                    timestamp
                )
            
            self.equity_curve.append({
                'time': timestamp,
                'equity': total_value,
                'cash': self.cash,
                'positions': len(self.positions),
                'market_state': result['index']
            })
        
        final_value = self.get_total_value(df['close'].iloc[-1])
        
        return self.calculate_metrics(final_value)
    
    def calculate_metrics(self, final_value: float) -> Dict:
        equity_df = pd.DataFrame(self.equity_curve)
        returns = equity_df['equity'].pct_change().dropna()
        
        total_return = (final_value - self.initial_krw) / self.initial_krw * 100
        
        winning_trades = [t for t in self.trades if t.get('pnl', 0) > 0]
        losing_trades = [t for t in self.trades if t.get('pnl', 0) < 0]
        
        win_rate = len(winning_trades) / max(1, len(winning_trades) + len(losing_trades)) * 100
        
        avg_win = np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0
        avg_loss = abs(np.mean([t['pnl'] for t in losing_trades])) if losing_trades else 0
        profit_factor = avg_win / max(avg_loss, 1) if avg_loss > 0 else avg_win
        
        max_drawdown = 0
        peak = equity_df['equity'].iloc[0]
        for value in equity_df['equity']:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak * 100
            max_drawdown = max(max_drawdown, drawdown)
        
        daily_returns = returns * 288
        sharpe_ratio = np.sqrt(365) * daily_returns.mean() / (daily_returns.std() + 1e-9)
        
        total_fees = sum(t['fee'] for t in self.trades)
        
        stage_stats = pd.DataFrame(self.market_states).groupby('index').size()
        
        return {
            'initial_capital': self.initial_krw,
            'final_value': final_value,
            'total_return_pct': total_return,
            'total_trades': len([t for t in self.trades if t['type'] == 'BUY']),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate_pct': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'max_drawdown_pct': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'total_fees_paid': total_fees,
            'fee_impact_pct': (total_fees / self.initial_krw) * 100,
            'market_stage_distribution': stage_stats.to_dict() if not stage_stats.empty else {}
        }
    
    def save_results(self, filename: str = 'backtest_results.json'):
        results = {
            'metrics': self.calculate_metrics(self.get_total_value(self.equity_curve[-1]['equity'])),
            'trades': self.trades[-20:],
            'equity_curve': self.equity_curve[::10],
            'timestamp': datetime.now().isoformat()
        }
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        return results

def quick_backtest(csv_path: str, initial_krw: float = 1_000_000):
    engine = BacktestEngine(initial_krw=initial_krw, fee_rate=0.0005)
    df = pd.read_csv(csv_path)
    results = engine.run(df)
    
    print("\n=== Backtest Results ===")
    print(f"Initial Capital: {results['initial_capital']:,.0f} KRW")
    print(f"Final Value: {results['final_value']:,.0f} KRW")
    print(f"Total Return: {results['total_return_pct']:.2f}%")
    print(f"Total Trades: {results['total_trades']}")
    print(f"Win Rate: {results['win_rate_pct']:.2f}%")
    print(f"Profit Factor: {results['profit_factor']:.2f}")
    print(f"Max Drawdown: {results['max_drawdown_pct']:.2f}%")
    print(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
    print(f"Total Fees: {results['total_fees_paid']:,.0f} KRW ({results['fee_impact_pct']:.2f}%)")
    
    if results['market_stage_distribution']:
        print("\n=== Market Stage Distribution ===")
        for stage, count in sorted(results['market_stage_distribution'].items()):
            print(f"Stage {stage}: {count} periods")
    
    engine.save_results()
    return results

if __name__ == "__main__":
    print("Backtest Engine Ready!")
    print("Usage: quick_backtest('your_data.csv', initial_krw=1000000)")
    print("\nCSV should have columns: date/timestamp, open, high, low, close, volume")