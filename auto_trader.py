# -*- coding: utf-8 -*-
import time
import pyupbit
import datetime
import pandas as pd
import numpy as np
from strategy_engine import decide_order, RiskManager, calc_market_snapshot, calc_market_index
from monitor import TradingMonitor
from correlation_manager import CorrelationManager
import json
import threading

class FullAutoTrader:
    def __init__(self, tickers=None, max_coins=None):
        """
        완전 자동 트레이더
        tickers: 거래할 코인 리스트 (None이면 상위 거래량 코인 자동 선택)
        max_coins: 최대 동시 보유 코인 수
        """
        # 설정 로드
        from config import Config, setup_environment
        
        if not setup_environment():
            raise ValueError("환경 설정이 올바르지 않습니다. .env 파일을 확인하세요.")
        
        # API 키 설정
        self.access_key = Config.UPBIT_ACCESS_KEY
        self.secret_key = Config.UPBIT_SECRET_KEY
        
        if not self.access_key or not self.secret_key:
            raise ValueError("Upbit API 키가 설정되지 않았습니다")
        
        self.upbit = pyupbit.Upbit(self.access_key, self.secret_key)
        
        # 설정에서 리스크 매니저 초기화
        self.risk_manager = RiskManager()
        self.risk_manager.max_position_pct = Config.MAX_POSITION_PCT
        self.risk_manager.max_trade_risk_pct = Config.MAX_TRADE_RISK_PCT
        self.risk_manager.daily_loss_limit_pct = Config.DAILY_LOSS_LIMIT_PCT
        
        self.monitor = TradingMonitor()
        
        # 상관관계 매니저 초기화
        self.correlation_manager = CorrelationManager(max_correlation=0.7, analysis_period=30)
        
        # 거래 설정
        self.max_coins = max_coins or Config.MAX_CONCURRENT_POSITIONS
        self.min_order_amount = Config.MIN_ORDER_AMOUNT
        self.positions = {}  # 현재 포지션들
        
        # 거래할 코인 자동 선택 또는 지정
        if tickers:
            self.tickers = tickers
        else:
            self.tickers = self.get_top_volume_tickers()
        
        print(f"Full Auto Trader Initialized")
        print(f"Trading Coins: {', '.join(self.tickers)}")
        print(f"Max Concurrent Positions: {max_coins}")
        
        # 텔레그램 시작 알림 (잔고 확인 후)
        try:
            krw_balance = self.upbit.get_balance("KRW")
            if krw_balance is not None:
                self.monitor.telegram.send_startup_message(self.tickers, krw_balance)
        except Exception as e:
            print(f"⚠️ 텔레그램 시작 알림 오류: {e}")
        
        self.analyze_current_status()
    
    def get_top_volume_tickers(self, top_n=5):
        """고도화된 시장 분석으로 최적 코인 선택"""
        try:
            from market_analyzer import MarketAnalyzer
            
            print("🔍 Advanced Market Analysis Starting...")
            analyzer = MarketAnalyzer()
            
            # 잔고에 따른 추천 받기
            try:
                krw_balance = self.upbit.get_balance("KRW")
                if krw_balance is None:
                    krw_balance = 1_000_000  # 기본값 사용
            except Exception as e:
                print(f"Balance retrieval error: {e}")
                krw_balance = 1_000_000  # 기본값 사용
                
            recommendations = analyzer.get_trading_recommendations(balance=krw_balance)
            
            # 균형잡힌 포트폴리오 구성
            selected = []
            
            # 1. 균형잡힌 코인 우선 (안정성)
            if recommendations['balanced']:
                selected.extend(recommendations['balanced'][:2])
            
            # 2. 공격적 코인 1개 (수익성)
            if recommendations['aggressive'] and len(selected) < top_n:
                selected.extend(recommendations['aggressive'][:1])
            
            # 3. 보수적 코인으로 보완
            if len(selected) < top_n and recommendations['conservative']:
                selected.extend(recommendations['conservative'][:top_n-len(selected)])
            
            # 4. 부족하면 상위 거래량에서 추가
            if len(selected) < top_n:
                top_coins = analyzer.get_top_coins(top_n=10, min_volume=5_000_000_000)
                for ticker, _ in top_coins:
                    if ticker not in selected:
                        selected.append(ticker)
                        if len(selected) >= top_n:
                            break
            
            print(f"✅ Selected {len(selected)} optimal coins for trading")
            
            # 상관관계를 고려한 최종 선택
            if len(selected) > top_n:
                print("🔄 Applying correlation-based diversification...")
                # 상관관계 매트릭스 업데이트
                if self.correlation_manager.update_correlation_matrix(selected):
                    selected = self.correlation_manager.get_diversified_portfolio(selected, top_n)
                else:
                    print("⚠️ Using original selection due to correlation analysis failure")
                    selected = selected[:top_n]
            
            return selected
            
        except Exception as e:
            print(f"Error in advanced selection, using fallback: {e}")
            # 기본 방식으로 폴백
            tickers = pyupbit.get_tickers(fiat="KRW")
            volumes = {}
            
            for ticker in tickers[:20]:
                try:
                    df = pyupbit.get_ohlcv(ticker, interval="day", count=1)
                    if df is not None and not df.empty and len(df) > 0:
                        volume_krw = df['volume'].iloc[-1] * df['close'].iloc[-1]
                        if volume_krw is not None and volume_krw > 0:
                            volumes[ticker] = volume_krw
                except Exception as e:
                    print(f"⚠️ {ticker} 데이터 오류 (폴백): {e}")
                    continue
                time.sleep(0.1)
            
            sorted_tickers = sorted(volumes.items(), key=lambda x: x[1], reverse=True)
            selected = []
            
            exclude_list = ['KRW-USDT', 'KRW-USDC', 'KRW-BUSD', 'KRW-WEMIX', 'KRW-DAI']
            for ticker, vol in sorted_tickers:
                if ticker not in exclude_list and vol and vol > 1_000_000_000:  # 최소 10억원 거래량
                    selected.append(ticker)
                    if len(selected) >= top_n:
                        break
            
            # 충분한 코인이 없으면 안전한 기본 코인들 추가
            if len(selected) < 3:
                safe_coins = ['KRW-BTC', 'KRW-ETH', 'KRW-XRP', 'KRW-ADA', 'KRW-DOT']
                for coin in safe_coins:
                    if coin not in selected:
                        selected.append(coin)
                        if len(selected) >= top_n:
                            break
            
            return selected
    
    def get_win_rate(self) -> float:
        """현재 승률 계산"""
        if len(self.risk_manager.trade_history) < 1:
            return 0.5
        wins = sum(1 for trade in self.risk_manager.trade_history if trade['win'])
        return wins / len(self.risk_manager.trade_history)
    
    def staged_profit_taking(self, ticker: str, entry_price: float, current_price: float) -> dict:
        """다단계 이익실현 시스템"""
        profit_pct = (current_price / entry_price - 1) * 100
        
        # 포지션 가치 확인 (부분 매도 가능 여부 판단)
        coin = ticker.split("-")[1]
        try:
            coin_balance = self.upbit.get_balance(coin)
            position_value = coin_balance * current_price if coin_balance else 0
        except:
            position_value = 0
        
        # 포지션이 충분히 큰 경우에만 부분 매도
        MIN_PARTIAL_SELL_VALUE = 20000  # 최소 2만원 이상일 때만 부분 매도
        
        if profit_pct >= 10:
            # 10% 이상은 전체 매도
            return {"action": "full_sell", "ratio": 1.0, "reason": "10% 달성 - 전체 매도"}
        elif profit_pct >= 8:
            if position_value >= MIN_PARTIAL_SELL_VALUE:
                return {"action": "partial_sell", "ratio": 0.5, "reason": "8% 달성 - 50% 매도"}
            else:
                return {"action": "full_sell", "ratio": 1.0, "reason": "8% 달성 - 전체 매도 (소액)"}
        elif profit_pct >= 5:
            if position_value >= MIN_PARTIAL_SELL_VALUE * 2:  # 4만원 이상일 때만 30% 매도
                return {"action": "partial_sell", "ratio": 0.3, "reason": "5% 달성 - 30% 매도"}
            else:
                # 소액이면 손절 상향만
                new_sl = entry_price * 1.03  # 손절 3% 상향
                return {"action": "adjust_sl", "new_sl": new_sl, "reason": "5% 달성 - 손절 상향 (소액)"}
        elif profit_pct >= 3:
            new_sl = entry_price * 1.02  # 손절 2% 상향
            return {"action": "adjust_sl", "new_sl": new_sl, "reason": "3% 달성 - 손절 상향"}
        elif profit_pct >= 1.5:
            new_sl = entry_price * 1.005  # 손절 0.5% 상향 (본전)
            return {"action": "adjust_sl", "new_sl": new_sl, "reason": "1.5% 달성 - 손절 본전"}
        
        return {"action": "hold"}
    
    def analyze_current_status(self):
        """현재 잔고 및 포지션 분석"""
        print("\n" + "="*60)
        print("CURRENT ACCOUNT STATUS")
        print("="*60)
        
        # 실제 KRW 잔고 가져오기
        try:
            krw_balance = self.upbit.get_balance("KRW")
            if krw_balance is None:
                print("❌ 잔고를 가져올 수 없습니다. API 키를 확인하세요.")
                return 0, 0, []
        except Exception as e:
            print(f"❌ API 연결 오류: {e}")
            print("💡 다음을 확인하세요:")
            print("  1. .env 파일의 API 키가 올바른지")
            print("  2. API 키에 조회 권한이 있는지")  
            print("  3. IP 허용 목록에 추가되었는지")
            print("  4. 네트워크 연결 상태")
            return 0, 0, []
        
        total_value = krw_balance
        
        print(f"KRW Balance: {krw_balance:,.0f} KRW")
        
        # 보유 코인 확인
        balances = self.upbit.get_balances()
        coin_holdings = []
        
        for balance in balances:
            if balance['currency'] != 'KRW' and float(balance['balance']) > 0:
                ticker = f"KRW-{balance['currency']}"
                if ticker in pyupbit.get_tickers(fiat="KRW"):
                    current_price = pyupbit.get_current_price(ticker)
                    coin_value = float(balance['balance']) * current_price
                    
                    if coin_value > 1000:  # 1000원 이상만 표시
                        coin_holdings.append({
                            'ticker': ticker,
                            'balance': float(balance['balance']),
                            'avg_price': float(balance['avg_buy_price']),
                            'current_price': current_price,
                            'value': coin_value,
                            'pnl': (current_price / float(balance['avg_buy_price']) - 1) * 100 if float(balance['avg_buy_price']) > 0 else 0
                        })
                        total_value += coin_value
        
        if coin_holdings:
            print("\nCurrent Holdings:")
            for holding in coin_holdings:
                print(f"  {holding['ticker']}: {holding['balance']:.8f} @ {holding['avg_price']:,.0f}")
                print(f"    Current: {holding['current_price']:,.0f} ({holding['pnl']:+.2f}%)")
                print(f"    Value: {holding['value']:,.0f} KRW")
                
                # 기존 포지션으로 등록
                self.positions[holding['ticker']] = {
                    'qty': holding['balance'],
                    'entry_price': holding['avg_price'],
                    'current_price': holding['current_price'],
                    'entry_time': datetime.datetime.now(),
                    'tp': holding['avg_price'] * 1.05,  # 기본 TP 5%
                    'sl': holding['avg_price'] * 0.97   # 기본 SL 3%
                }
        
        print(f"\nTotal Portfolio Value: {total_value:,.0f} KRW")
        print(f"Available for Trading: {krw_balance:,.0f} KRW")
        print(f"Current Positions: {len(coin_holdings)}/{self.max_coins}")
        print("="*60)
        
        print(f"\n💰 실제 잔고 기반 자동 거래:")
        print(f"  - KRW 잔고: {krw_balance:,.0f}원을 활용")
        print(f"  - 최대 {self.max_coins}개 코인 동시 거래")
        print(f"  - 코인당 최대 {self.risk_manager.max_position_pct:.0%} 할당")
        
        return krw_balance, total_value, coin_holdings
    
    def get_allocation_amount(self, krw_balance):
        """포지션당 할당 금액 계산"""
        # 남은 슬롯 수 계산
        remaining_slots = self.max_coins - len(self.positions)
        
        if remaining_slots <= 0:
            return 0
        
        # 슬롯당 할당 금액 (보수적으로 80%만 사용)
        allocation = (krw_balance * 0.8) / remaining_slots
        
        # 최소/최대 제한
        allocation = max(self.min_order_amount, min(allocation, krw_balance * 0.3))
        
        return allocation
    
    def analyze_and_trade(self, ticker):
        """특정 코인 분석 및 거래"""
        try:
            # 이미 포지션이 있는지 확인
            if ticker in self.positions:
                return self.manage_position(ticker)
            
            # 최대 포지션 수 체크
            if len(self.positions) >= self.max_coins:
                return
            
            # 시장 데이터 가져오기
            df = pyupbit.get_ohlcv(ticker, interval="minute1", count=200)
            if df is None or df.empty:
                print(f"⚠️ {ticker} 시장 데이터를 가져올 수 없습니다")
                return
            
            # pyupbit DataFrame은 이미 올바른 컬럼명을 가지고 있음
            # 컬럼명 확인만 하고 그대로 사용
            if 'close' not in df.columns:
                print(f"⚠️ {ticker} DataFrame missing 'close' column: {list(df.columns)}")
                return
            
            # 시장 분석
            snap = calc_market_snapshot(df)
            market_index = calc_market_index(snap)
            
            # 잔고 확인
            try:
                krw_balance = self.upbit.get_balance("KRW")
                if krw_balance is None:
                    print(f"⚠️ {ticker} 잔고 조회 실패")
                    return
            except Exception as e:
                print(f"⚠️ {ticker} API 오류: {e}")
                return
            
            allocation = self.get_allocation_amount(krw_balance)
            
            if allocation < self.min_order_amount:
                return
            
            # 거래 신호 확인
            result = decide_order(df, allocation, self.risk_manager)
            
            if result['plan']:
                plan = result['plan']
                # 실시간 가격 사용 (더 정확함)
                current_price = pyupbit.get_current_price(ticker)
                if not current_price:
                    current_price = df['close'].iloc[-1]
                
                # 상관관계 체크 (새로운 포지션 진입시)
                current_tickers = list(self.positions.keys())
                corr_check = self.correlation_manager.check_portfolio_correlation(current_tickers, ticker)
                
                if not corr_check['allowed']:
                    print(f"🚫 {ticker} 거래 제외 - {corr_check['reason']}")
                    return
                
                # 거래 수량 재계산
                order_amount = min(allocation, plan['qty'] * current_price * 1.0005)
                
                print(f"\n📊 {ticker} - Market State: {result['stage_name']}")
                print(f"   Signal: {plan['note']}")
                print(f"   Price: {current_price:,.0f} KRW")
                print(f"   Amount: {order_amount:,.0f} KRW")
                
                # 매수 실행
                order = self.upbit.buy_market_order(ticker, order_amount)
                
                if order:
                    # 포지션 등록
                    self.positions[ticker] = {
                        'qty': order_amount / current_price,
                        'entry_price': current_price,
                        'tp': plan['tp'],
                        'sl': plan['sl'],
                        'entry_time': datetime.datetime.now(),
                        'note': plan['note'],
                        'order_id': order.get('uuid')
                    }
                    
                    print(f"✅ {ticker} Buy Order Executed!")
                    print(f"   TP: {plan['tp']:,.0f} ({((plan['tp']/current_price-1)*100):+.2f}%)")
                    print(f"   SL: {plan['sl']:,.0f} ({((plan['sl']/current_price-1)*100):+.2f}%)")
                    
                    self.monitor.log_trade('BUY', current_price, plan['qty'], 
                                         plan['note'], ticker, plan['tp'], plan['sl'])
                    
        except Exception as e:
            print(f"Error trading {ticker}: {e}")
    
    def manage_position(self, ticker):
        """기존 포지션 관리"""
        try:
            if ticker not in self.positions:
                return
            
            pos = self.positions[ticker]
            try:
                current_price = pyupbit.get_current_price(ticker)
            except Exception as e:
                print(f"❌ {ticker} 현재가 조회 실패: {e}")
                return
                
            if not current_price:
                print(f"⚠️ {ticker} 현재가 없음")
                return
            
            # PnL 계산
            pnl_pct = (current_price / pos['entry_price'] - 1) * 100
            
            # 현재 포지션 상태 출력 (매 사이클마다)
            hold_time = (datetime.datetime.now() - pos['entry_time']).total_seconds() / 3600  # 시간 단위
            print(f"📊 {ticker} 포지션 상태:")
            print(f"   진입가: {pos['entry_price']:,.0f}, 현재가: {current_price:,.0f}")
            print(f"   PnL: {pnl_pct:+.2f}%, 보유시간: {hold_time:.1f}시간")
            print(f"   TP: {pos['tp']:,.0f}, SL: {pos['sl']:,.0f}")
            
            # 다단계 이익실현 로직 적용
            profit_action = self.staged_profit_taking(ticker, pos['entry_price'], current_price)
            
            # TP/SL 체크
            should_sell = False
            partial_sell = False
            sell_ratio = 1.0
            reason = ""
            
            # 다단계 이익실현 처리
            if profit_action['action'] == 'partial_sell':
                partial_sell = True
                sell_ratio = profit_action['ratio']
                reason = profit_action['reason']
                should_sell = True
            elif profit_action['action'] == 'full_sell':
                partial_sell = False
                sell_ratio = 1.0
                reason = profit_action['reason']
                should_sell = True
            elif profit_action['action'] == 'adjust_sl':
                # SL 상향 조정
                pos['sl'] = profit_action['new_sl']
                print(f"📈 {ticker} SL 상향: {profit_action['new_sl']:,.0f} - {profit_action['reason']}")
            
            # 매도 조건 체크
            print(f"🔍 매도 조건 체크:")
            print(f"   TP 도달: {current_price >= pos['tp']} (현재: {current_price:,.0f} >= TP: {pos['tp']:,.0f})")
            print(f"   SL 도달: {current_price <= pos['sl']} (현재: {current_price:,.0f} <= SL: {pos['sl']:,.0f})")
            print(f"   보유시간: {hold_time:.1f}시간, 수익여부: {pnl_pct > 0}")
            
            # 기존 TP/SL 체크
            if not should_sell:
                if current_price >= pos['tp']:
                    should_sell = True
                    reason = "Take Profit"
                    print(f"✅ TP 조건 달성!")
                elif current_price <= pos['sl']:
                    should_sell = True
                    reason = "Stop Loss"
                    print(f"✅ SL 조건 달성!")
                elif (datetime.datetime.now() - pos['entry_time']).total_seconds() > 86400:  # 24시간
                    if pnl_pct > 0:
                        should_sell = True
                        reason = "Time Exit (Profit)"
                        print(f"✅ 24시간 수익 매도 조건 달성!")
                elif (datetime.datetime.now() - pos['entry_time']).total_seconds() > 172800:  # 48시간 강제 종료
                    should_sell = True
                    reason = "Time Exit (Force)"
                    print(f"✅ 48시간 강제 매도 조건 달성!")
            
            if not should_sell:
                print(f"❌ 매도 조건 미달성 - 보유 유지")
            
            if should_sell:
                coin = ticker.split("-")[1]
                try:
                    coin_balance = self.upbit.get_balance(coin)
                    print(f"🔍 {ticker} 잔고 확인: {coin_balance:.8f}")
                except Exception as e:
                    print(f"❌ {ticker} 잔고 조회 오류: {e}")
                    return
                
                if coin_balance and coin_balance > 0.00000001:  # 최소 잔고 체크
                    # 매도할 수량 계산
                    sell_amount = coin_balance * sell_ratio if partial_sell else coin_balance
                    sell_value = sell_amount * current_price
                    
                    # 최소 거래금액 체크 (5000원)
                    MIN_TRADE_AMOUNT = 5000
                    if sell_value < MIN_TRADE_AMOUNT:
                        if partial_sell:
                            # 부분 매도시 최소 금액 미달이면 전체 매도로 전환
                            print(f"⚠️ 부분 매도 금액({sell_value:,.0f}원)이 최소 거래금액 미만")
                            
                            # 전체 잔고 가치 확인
                            total_value = coin_balance * current_price
                            if total_value >= MIN_TRADE_AMOUNT:
                                print(f"🔄 전체 매도로 전환 (총 {total_value:,.0f}원)")
                                sell_amount = coin_balance
                                sell_value = total_value
                                partial_sell = False  # 전체 매도로 변경
                                sell_ratio = 1.0
                            else:
                                print(f"❌ 전체 잔고도 최소 거래금액 미만 ({total_value:,.0f}원)")
                                # 포지션 제거 (매도 불가)
                                del self.positions[ticker]
                                print(f"🗑️ 포지션 제거 (매도 불가)")
                                return
                        else:
                            print(f"❌ 매도 금액({sell_value:,.0f}원)이 최소 거래금액({MIN_TRADE_AMOUNT}원) 미만")
                            return
                    
                    print(f"\n💰 {'Partial' if partial_sell else 'Full'} Closing {ticker} Position - {reason}")
                    print(f"   Entry: {pos['entry_price']:,.0f}")
                    print(f"   Exit: {current_price:,.0f}")
                    print(f"   PnL: {pnl_pct:+.2f}%")
                    print(f"   매도 금액: {sell_value:,.0f} KRW")
                    if partial_sell:
                        print(f"   Selling: {sell_ratio:.1%} of position")
                    
                    # 매도 실행
                    print(f"🔄 매도 주문 실행 중: {sell_amount:.8f} {coin} (가치: {sell_value:,.0f}원)")
                    
                    try:
                        order = self.upbit.sell_market_order(ticker, sell_amount)
                        print(f"📝 매도 주문 결과: {order}")
                    except Exception as e:
                        print(f"❌ 매도 주문 실패: {e}")
                        return
                    
                    if order and 'uuid' in order:
                        # PnL 업데이트
                        pnl = (current_price - pos['entry_price']) * sell_amount
                        self.risk_manager.update_pnl(pnl)
                        self.monitor.log_exit(reason, current_price, sell_amount, pnl, pnl_pct, ticker, pos['entry_price'])
                        
                        if partial_sell:
                            # 부분 매도: 포지션 수량 업데이트
                            remaining_qty = coin_balance - sell_amount
                            if remaining_qty > 0.00000001:
                                self.positions[ticker]['qty'] = remaining_qty
                                print(f"✅ Partial Position Closed! Remaining: {remaining_qty:.8f}")
                            else:
                                # 남은 수량이 너무 적으면 포지션 완전 제거
                                del self.positions[ticker]
                                print(f"✅ Position Fully Closed! (Remaining too small)")
                        else:
                            # 전체 매도: 포지션 제거
                            del self.positions[ticker]
                            print(f"✅ Position Fully Closed!")
                    else:
                        print(f"❌ 매도 주문 실패 또는 응답 없음: {order}")
                else:
                    print(f"⚠️ {ticker} 매도 불가 - 잔고 부족: {coin_balance:.8f}")
                    
        except Exception as e:
            print(f"Error managing position {ticker}: {e}")
    
    def check_and_replace_underperforming_tickers(self):
        """거래량이 급감한 종목 즉시 교체"""
        if len(self.positions) >= self.max_coins:
            return  # 포지션이 가득 차면 교체 불필요
        
        try:
            # 현재 티커들의 거래량 확인
            current_volumes = {}
            for ticker in self.tickers:
                if ticker not in self.positions:  # 포지션 없는 종목만 체크
                    try:
                        df = pyupbit.get_ohlcv(ticker, interval="day", count=1)
                        if df is not None and not df.empty:
                            volume_krw = df['volume'].iloc[-1] * df['close'].iloc[-1]
                            current_volumes[ticker] = volume_krw
                    except:
                        current_volumes[ticker] = 0
            
            # 거래량이 10억원 미만인 종목 찾기
            MIN_VOLUME = 1_000_000_000
            underperformers = [t for t, v in current_volumes.items() if v < MIN_VOLUME]
            
            if underperformers:
                print(f"\n⚠️ 거래량 부족 종목 발견: {', '.join(underperformers)}")
                
                # 새로운 종목 후보 가져오기
                new_candidates = self.get_top_volume_tickers()
                
                # 현재 리스트에 없는 종목만 선택
                replacements = [t for t in new_candidates if t not in self.tickers]
                
                # 교체 실행
                for old_ticker in underperformers:
                    if replacements:
                        new_ticker = replacements.pop(0)
                        idx = self.tickers.index(old_ticker)
                        self.tickers[idx] = new_ticker
                        print(f"🔄 종목 교체: {old_ticker} → {new_ticker}")
                
                # 상관관계 매트릭스 업데이트
                if underperformers:
                    self.correlation_manager.update_correlation_matrix(self.tickers)
                    
        except Exception as e:
            print(f"종목 교체 체크 중 오류: {e}")
    
    def run_cycle(self):
        """전체 코인 순회 및 거래"""
        print(f"\n🔄 Trading Cycle - {datetime.datetime.now().strftime('%H:%M:%S')}")
        
        # 거래량 급감 종목 체크 및 교체
        self.check_and_replace_underperforming_tickers()
        
        # 현재 상태 확인
        krw_balance, total_value, _ = self.analyze_current_status()
        
        # 리스크 체크
        if self.risk_manager.daily_pnl < -total_value * 0.05:
            print("⚠️ Daily loss limit reached. Pausing trading...")
            return False
        
        # 각 코인 분석 및 거래
        for ticker in self.tickers:
            try:
                # 포지션 관리 또는 신규 진입
                if ticker in self.positions:
                    self.manage_position(ticker)
                else:
                    self.analyze_and_trade(ticker)
                
                time.sleep(0.5)  # API 제한 방지
                
            except Exception as e:
                print(f"Error processing {ticker}: {e}")
        
        # 포트폴리오 리스크 분석
        if len(self.positions) > 1:
            risk_metrics = self.correlation_manager.get_portfolio_risk_metrics(list(self.positions.keys()))
        else:
            risk_metrics = {"risk_score": "LOW", "max_correlation": 0.0}
        
        # 요약 출력
        print(f"\n📈 Cycle Summary:")
        print(f"   Active Positions: {len(self.positions)}")
        print(f"   Daily PnL: {self.risk_manager.daily_pnl:+,.0f} KRW")
        print(f"   Win Rate: {self.get_win_rate():.1%}")
        print(f"   Portfolio Risk: {risk_metrics['risk_score']} (Max Corr: {risk_metrics['max_correlation']:.2f})")
        print(f"   Next cycle in 1 minutes...")  # 1분
        
        return True
    
    def run(self):
        """메인 실행 루프"""
        print("\n" + "="*60)
        print("STARTING FULL AUTO TRADING SYSTEM")
        print("="*60)
        print(f"Trading Coins: {', '.join(self.tickers)}")
        print(f"Max Positions: {self.max_coins}")
        print("Update Interval: 1 minutes")  
        print("="*60 + "\n")
        
        # 일일 리셋 스케줄러
        last_reset = datetime.datetime.now().date()
        last_ticker_update = datetime.datetime.now()
        ticker_update_interval = 4  # 4시간마다 종목 재평가
        
        while True:
            try:
                # 일일 리셋 체크
                current_date = datetime.datetime.now().date()
                if current_date != last_reset:
                    self.risk_manager.reset_daily()
                    
                    # 매일 거래 종목 재선정 (포지션이 없는 경우만)
                    if len(self.positions) == 0:
                        print("🔄 거래 종목 재선정 중...")
                        new_tickers = self.get_top_volume_tickers()
                        if new_tickers != self.tickers:
                            print(f"📊 거래 종목 변경:")
                            print(f"   기존: {', '.join(self.tickers)}")
                            print(f"   신규: {', '.join(new_tickers)}")
                            self.tickers = new_tickers
                        else:
                            print("✅ 거래 종목 변경 없음")
                    
                    # 상관관계 매트릭스도 업데이트
                    if self.correlation_manager.should_update_matrix():
                        print("🔄 Updating correlation matrix...")
                        self.correlation_manager.update_correlation_matrix(self.tickers)
                    
                    last_reset = current_date
                    print("\n🔄 Daily reset completed")
                
                # 4시간마다 종목 재평가 (포지션이 없거나 적을 때)
                hours_since_update = (datetime.datetime.now() - last_ticker_update).total_seconds() / 3600
                if hours_since_update >= ticker_update_interval and len(self.positions) <= 1:
                    print(f"\n🔄 {ticker_update_interval}시간 경과 - 거래 종목 재평가")
                    
                    # 현재 포지션 있는 종목은 유지
                    protected_tickers = list(self.positions.keys())
                    
                    # 새로운 종목 가져오기
                    new_tickers = self.get_top_volume_tickers()
                    
                    # 포지션 있는 종목은 보호하면서 리스트 업데이트
                    updated_tickers = protected_tickers.copy()
                    for ticker in new_tickers:
                        if ticker not in updated_tickers and len(updated_tickers) < 5:
                            updated_tickers.append(ticker)
                    
                    if updated_tickers != self.tickers:
                        print(f"📊 거래 종목 업데이트:")
                        print(f"   기존: {', '.join(self.tickers)}")
                        print(f"   신규: {', '.join(updated_tickers)}")
                        print(f"   보호된 포지션: {', '.join(protected_tickers) if protected_tickers else '없음'}")
                        self.tickers = updated_tickers
                        
                        # 상관관계 매트릭스 업데이트
                        self.correlation_manager.update_correlation_matrix(self.tickers)
                    else:
                        print("✅ 거래 종목 변경 없음")
                    
                    last_ticker_update = datetime.datetime.now()
                
                # 거래 사이클 실행
                if self.run_cycle():
                    time.sleep(60)  # 1분 대기
                else:
                    time.sleep(3600)  # 손실 한도시 1시간 대기
                
            except KeyboardInterrupt:
                print("\n\nAuto Trading Stopped")
                self.monitor.print_summary()
                break
                
            except Exception as e:
                print(f"System error: {e}")
                time.sleep(60)

def main():
    # 옵션 1: 자동으로 거래량 상위 코인 선택
    trader = FullAutoTrader(max_coins=3)
    
    # 옵션 2: 특정 코인 지정
    # trader = FullAutoTrader(
    #     tickers=['KRW-BTC', 'KRW-ETH', 'KRW-XRP'],
    #     max_coins=3
    # )
    
    trader.run()

if __name__ == "__main__":
    main()