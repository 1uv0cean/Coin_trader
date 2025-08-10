# -*- coding: utf-8 -*-
import logging
import json
from datetime import datetime
from typing import Dict, Optional, List
import pandas as pd
from telegram_bot import TelegramNotifier

class TradingMonitor:
    def __init__(self, log_file: str = 'trading_log.json'):
        self.log_file = log_file
        self.alerts = []
        self.performance_stats = {}
        
        # 텔레그램 알림 초기화
        self.telegram = TelegramNotifier()
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s | %(levelname)s | %(message)s',
            handlers=[
                logging.FileHandler('trading.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def log_market_state(self, index: int, stage_name: str, snapshot: Dict, ticker: str = "KRW-BTC"):
        msg = f"Market State: {stage_name} | RSI: {snapshot.get('rsi', 0):.1f} | Volume: {snapshot.get('volume_rel_5d', 0):.2f}x"
        self.logger.info(msg)
        
        # 텔레그램 시장 상태 알림 (중요한 단계만)
        if index <= 2 or index >= 7:
            momentum = (snapshot.get('close_changes_1d', 0) + 
                       snapshot.get('close_changes_3d', 0) + 
                       snapshot.get('close_changes_7d', 0)) / 3
            
            self.telegram.send_market_alert(
                stage=index,
                stage_name=stage_name,
                ticker=ticker,
                rsi=snapshot.get('rsi', 0),
                volume_ratio=snapshot.get('volume_rel_5d', 0),
                momentum=momentum
            )
        
        if index <= 1:
            self.add_alert("EXTREME_FEAR", f"Market in extreme fear zone ({stage_name})")
        elif index >= 8:
            self.add_alert("EXTREME_GREED", f"Market in extreme greed zone ({stage_name})")
    
    def log_trade(self, trade_type: str, price: float, qty: float, note: str, 
                  ticker: str = "KRW-BTC", tp: Optional[float] = None, sl: Optional[float] = None):
        trade_info = {
            'timestamp': datetime.now().isoformat(),
            'type': trade_type,
            'ticker': ticker,
            'price': price,
            'qty': qty,
            'note': note,
            'tp': tp,
            'sl': sl
        }
        
        msg = f"TRADE: {trade_type} | {ticker} | Price: {price:,.0f} | Qty: {qty:.6f} | {note}"
        if tp and sl:
            msg += f" | TP: {tp:,.0f} | SL: {sl:,.0f}"
        
        self.logger.info(msg)
        self.save_trade(trade_info)
        
        # 텔레그램 거래 알림
        self.telegram.send_trade_alert(
            action=trade_type,
            ticker=ticker,
            price=price,
            qty=qty,
            strategy=note,
            tp=tp,
            sl=sl
        )
    
    def log_exit(self, exit_type: str, price: float, qty: float, pnl: float, pnl_pct: float, 
                 ticker: str = "KRW-BTC", entry_price: float = None):
        color = "🟢" if pnl > 0 else "🔴"
        msg = f"EXIT: {exit_type} | {ticker} | Price: {price:,.0f} | PnL: {pnl:+,.0f} ({pnl_pct:+.2f}%) {color}"
        self.logger.info(msg)
        
        # 텔레그램 청산 알림
        if entry_price:
            self.telegram.send_exit_alert(
                exit_type=exit_type,
                ticker=ticker,
                exit_price=price,
                entry_price=entry_price,
                qty=qty,
                pnl=pnl,
                pnl_pct=pnl_pct
            )
    
    def log_risk_alert(self, alert_type: str, message: str, balance: float = None):
        self.logger.warning(f"RISK ALERT: {alert_type} - {message}")
        self.add_alert(alert_type, message)
        
        # 텔레그램 리스크 알림
        self.telegram.send_risk_alert(alert_type, message, balance)
    
    def add_alert(self, alert_type: str, message: str):
        alert = {
            'timestamp': datetime.now().isoformat(),
            'type': alert_type,
            'message': message
        }
        self.alerts.append(alert)
        
        if len(self.alerts) > 100:
            self.alerts = self.alerts[-100:]
    
    def save_trade(self, trade_info: Dict):
        try:
            with open(self.log_file, 'r') as f:
                trades = json.load(f)
        except:
            trades = []
        
        trades.append(trade_info)
        
        if len(trades) > 1000:
            trades = trades[-1000:]
        
        with open(self.log_file, 'w') as f:
            json.dump(trades, f, indent=2)
    
    def calculate_daily_stats(self, trades: List[Dict]) -> Dict:
        if not trades:
            return {}
        
        df = pd.DataFrame(trades)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['date'] = df['timestamp'].dt.date
        
        today = datetime.now().date()
        today_trades = df[df['date'] == today]
        
        if today_trades.empty:
            return {}
        
        wins = today_trades[today_trades.get('pnl', 0) > 0]
        losses = today_trades[today_trades.get('pnl', 0) < 0]
        
        return {
            'date': str(today),
            'total_trades': len(today_trades),
            'wins': len(wins),
            'losses': len(losses),
            'total_pnl': today_trades['pnl'].sum() if 'pnl' in today_trades else 0,
            'win_rate': len(wins) / len(today_trades) * 100 if len(today_trades) > 0 else 0
        }
    
    def print_summary(self):
        print("\n" + "="*50)
        print("TRADING SESSION SUMMARY")
        print("="*50)
        
        try:
            with open(self.log_file, 'r') as f:
                trades = json.load(f)
            
            stats = self.calculate_daily_stats(trades)
            if stats:
                print(f"Date: {stats['date']}")
                print(f"Total Trades: {stats['total_trades']}")
                print(f"Wins/Losses: {stats['wins']}/{stats['losses']}")
                print(f"Win Rate: {stats['win_rate']:.1f}%")
                print(f"Total PnL: {stats['total_pnl']:+,.0f} KRW")
        except:
            print("No trading data available")
        
        if self.alerts:
            print("\nRECENT ALERTS:")
            for alert in self.alerts[-5:]:
                print(f"  • {alert['type']}: {alert['message']}")
        
        print("="*50)

class LiveTrader:
    def __init__(self, initial_balance: float = 1_000_000):
        self.monitor = TradingMonitor()
        self.balance = initial_balance
        self.positions = []
        
    def process_market_data(self, df: pd.DataFrame) -> Dict:
        from strategy_engine import decide_order, RiskManager
        
        risk_manager = RiskManager()
        result = decide_order(df, self.balance, risk_manager)
        
        self.monitor.log_market_state(
            result['index'],
            result['stage_name'],
            result['snapshot']
        )
        
        if result['plan']:
            plan = result['plan']
            self.monitor.log_trade(
                'BUY',
                df['close'].iloc[-1],
                plan['qty'],
                plan['note'],
                plan['tp'],
                plan['sl']
            )
        
        return result
    
    def check_positions(self, current_price: float, high: float, low: float):
        for pos in self.positions[:]:
            if pos['tp'] and high >= pos['tp']:
                pnl = (pos['tp'] - pos['entry_price']) * pos['qty']
                pnl_pct = (pos['tp'] / pos['entry_price'] - 1) * 100
                self.monitor.log_exit('TP', pos['tp'], pos['qty'], pnl, pnl_pct)
                self.positions.remove(pos)
            elif pos['sl'] and low <= pos['sl']:
                pnl = (pos['sl'] - pos['entry_price']) * pos['qty']
                pnl_pct = (pos['sl'] / pos['entry_price'] - 1) * 100
                self.monitor.log_exit('SL', pos['sl'], pos['qty'], pnl, pnl_pct)
                self.positions.remove(pos)
    
    def run_cycle(self, df: pd.DataFrame):
        result = self.process_market_data(df)
        
        current = df.iloc[-1]
        self.check_positions(current['close'], current['high'], current['low'])
        
        return result

if __name__ == "__main__":
    print("Trading Monitor System Initialized")
    monitor = TradingMonitor()
    monitor.print_summary()