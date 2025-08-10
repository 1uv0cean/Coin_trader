# -*- coding: utf-8 -*-
import time
import pyupbit
import datetime
import pandas as pd
import numpy as np
from strategy_engine import decide_order, RiskManager, calc_market_snapshot, calc_market_index
from monitor import TradingMonitor
import json

class LiveUpbitTrader:
    def __init__(self, ticker="KRW-BTC"):
        # API 키 로드
        with open("upbit.txt") as f:
            lines = f.readlines()
            self.access_key = lines[0].strip()
            self.secret_key = lines[1].strip()
        
        self.upbit = pyupbit.Upbit(self.access_key, self.secret_key)
        self.ticker = ticker
        self.risk_manager = RiskManager()
        self.monitor = TradingMonitor()
        
        # 포지션 추적
        self.current_position = None
        self.entry_price = 0
        self.position_qty = 0
        
        print(f"Live Trader initialized for {ticker}")
        self.check_balance()
    
    def check_balance(self):
        """잔고 확인"""
        krw_balance = self.upbit.get_balance("KRW")
        coin = self.ticker.split("-")[1]
        coin_balance = self.upbit.get_balance(coin)
        
        print(f"KRW Balance: {krw_balance:,.0f}")
        print(f"{coin} Balance: {coin_balance:.8f}")
        
        return krw_balance, coin_balance
    
    def get_market_data(self, interval="minute1", count=200):
        """시장 데이터 가져오기"""
        df = pyupbit.get_ohlcv(self.ticker, interval=interval, count=count)
        
        if df is None or df.empty:
            print("Failed to fetch market data")
            return None
        
        # pyupbit DataFrame은 이미 올바른 컬럼명을 가지고 있음
        # timestamp는 이미 인덱스로 존재
        df.reset_index(inplace=True)
        df.rename(columns={'index': 'timestamp'}, inplace=True)
        
        return df
    
    def analyze_market(self, df):
        """시장 상태 분석"""
        snap = calc_market_snapshot(df)
        market_index = calc_market_index(snap)
        
        # 시장 상태 로깅
        stage_names = [
            "0: Extreme Panic", "1: Strong Down", "2: Down Persist",
            "3: Weak Down", "4: Bearish Turn", "5: Neutral Box",
            "6: Bullish Turn", "7: Weak Up", "8: Strong Up", 
            "9: Extreme Greed"
        ]
        
        current_price = df['close'].iloc[-1]
        
        print(f"\n{'='*50}")
        print(f"Market Analysis - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*50}")
        print(f"Current Price: {current_price:,.0f} KRW")
        print(f"Market State: {stage_names[market_index]}")
        print(f"RSI: {snap.rsi:.1f}")
        print(f"Volume Ratio: {snap.volume_rel_5d:.2f}x")
        print(f"1D Change: {snap.close_changes_1d:+.2f}%")
        print(f"3D Change: {snap.close_changes_3d:+.2f}%")
        
        self.monitor.log_market_state(market_index, stage_names[market_index], snap.__dict__)
        
        return market_index, snap
    
    def execute_trade(self, df):
        """거래 실행"""
        krw_balance, coin_balance = self.check_balance()
        
        # 최소 거래 금액 체크
        if krw_balance < 5500:
            print("Insufficient KRW balance")
            return
        
        # 시장 분석 및 주문 결정
        result = decide_order(df, krw_balance, self.risk_manager)
        
        if result['plan']:
            plan = result['plan']
            current_price = df['close'].iloc[-1]
            
            # 거래 수량 계산 (수수료 고려)
            fee_rate = 0.0005
            order_amount = plan['qty'] * current_price
            total_cost = order_amount * (1 + fee_rate)
            
            if total_cost > krw_balance:
                print(f"Insufficient balance for order: {total_cost:,.0f} KRW needed")
                return
            
            # 매수 주문 실행
            try:
                print(f"\n📊 Executing Trade:")
                print(f"   Strategy: {plan['note']}")
                print(f"   Amount: {order_amount:,.0f} KRW")
                print(f"   Quantity: {plan['qty']:.8f}")
                print(f"   TP: {plan['tp']:,.0f} KRW ({((plan['tp']/current_price - 1)*100):+.2f}%)")
                print(f"   SL: {plan['sl']:,.0f} KRW ({((plan['sl']/current_price - 1)*100):+.2f}%)")
                
                # 실제 매수 주문
                order = self.upbit.buy_market_order(self.ticker, order_amount)
                
                if order:
                    self.current_position = {
                        'entry_price': current_price,
                        'qty': plan['qty'],
                        'tp': plan['tp'],
                        'sl': plan['sl'],
                        'entry_time': datetime.datetime.now(),
                        'note': plan['note']
                    }
                    
                    self.monitor.log_trade(
                        'BUY', current_price, plan['qty'], 
                        plan['note'], plan['tp'], plan['sl']
                    )
                    
                    print("✅ Order executed successfully!")
                    print(f"Order ID: {order.get('uuid', 'N/A')}")
                else:
                    print("❌ Order failed")
                    
            except Exception as e:
                print(f"❌ Order execution error: {e}")
                self.monitor.log_risk_alert("ORDER_ERROR", str(e))
        else:
            print("No trading signal at current market state")
    
    def check_exit_conditions(self):
        """출구 조건 확인"""
        if not self.current_position:
            return
        
        current_price = pyupbit.get_current_price(self.ticker)
        pos = self.current_position
        
        # TP/SL 체크
        if current_price >= pos['tp']:
            print(f"\n🎯 Take Profit Hit! Price: {current_price:,.0f}")
            self.close_position('TP', current_price)
            
        elif current_price <= pos['sl']:
            print(f"\n🛑 Stop Loss Hit! Price: {current_price:,.0f}")
            self.close_position('SL', current_price)
            
        # 시간 기반 출구 (선택적 - 24시간 이상 보유시)
        elif (datetime.datetime.now() - pos['entry_time']).seconds > 86400:
            print(f"\n⏰ Time-based exit after 24 hours")
            self.close_position('TIME', current_price)
    
    def close_position(self, exit_type, exit_price):
        """포지션 청산"""
        if not self.current_position:
            return
        
        pos = self.current_position
        coin = self.ticker.split("-")[1]
        coin_balance = self.upbit.get_balance(coin)
        
        if coin_balance > 0:
            try:
                # 시장가 매도
                order = self.upbit.sell_market_order(self.ticker, coin_balance)
                
                if order:
                    # PnL 계산
                    pnl = (exit_price - pos['entry_price']) * pos['qty']
                    pnl_pct = (exit_price / pos['entry_price'] - 1) * 100
                    
                    self.monitor.log_exit(exit_type, exit_price, pos['qty'], pnl, pnl_pct)
                    self.risk_manager.update_pnl(pnl)
                    
                    print(f"✅ Position closed: {pnl:+,.0f} KRW ({pnl_pct:+.2f}%)")
                    
                    self.current_position = None
                else:
                    print("❌ Failed to close position")
                    
            except Exception as e:
                print(f"❌ Position close error: {e}")
                self.monitor.log_risk_alert("CLOSE_ERROR", str(e))
    
    def run(self, interval_minutes=5):
        """메인 실행 루프"""
        print(f"\n{'='*50}")
        print(f"Starting Live Trading - {self.ticker}")
        print(f"Update Interval: {interval_minutes} minutes")
        print(f"{'='*50}\n")
        
        while True:
            try:
                # 시장 데이터 가져오기
                df = self.get_market_data()
                
                if df is not None:
                    # 시장 분석
                    market_index, snap = self.analyze_market(df)
                    
                    # 포지션 체크
                    if self.current_position:
                        print(f"\n📍 Active Position:")
                        print(f"   Entry: {self.current_position['entry_price']:,.0f}")
                        print(f"   Current: {df['close'].iloc[-1]:,.0f}")
                        print(f"   PnL: {((df['close'].iloc[-1]/self.current_position['entry_price'] - 1)*100):+.2f}%")
                        
                        # 출구 조건 확인
                        self.check_exit_conditions()
                    else:
                        # 새로운 거래 기회 확인
                        self.execute_trade(df)
                    
                    # 일일 리스크 체크
                    if self.risk_manager.daily_pnl < -50000:  # 5만원 손실시
                        print("\n⚠️ Daily loss limit reached. Trading paused.")
                        self.monitor.log_risk_alert("DAILY_LIMIT", "Daily loss limit reached")
                        time.sleep(3600)  # 1시간 대기
                
                # 다음 업데이트까지 대기
                print(f"\nNext update in {interval_minutes} minutes...")
                time.sleep(interval_minutes * 60)
                
            except KeyboardInterrupt:
                print("\n\nTrading stopped by user")
                self.monitor.print_summary()
                break
                
            except Exception as e:
                print(f"Error in main loop: {e}")
                self.monitor.log_risk_alert("SYSTEM_ERROR", str(e))
                time.sleep(60)  # 1분 후 재시도

def main():
    # 거래할 코인 선택
    ticker = "KRW-BTC"  # BTC, ETH, XRP 등으로 변경 가능
    
    # 트레이더 초기화 및 실행
    trader = LiveUpbitTrader(ticker)
    trader.run(interval_minutes=5)  # 5분 간격 업데이트

if __name__ == "__main__":
    main()