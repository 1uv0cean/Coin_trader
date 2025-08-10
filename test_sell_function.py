# -*- coding: utf-8 -*-
"""
매도 기능 테스트 스크립트
"""

import pyupbit
from config import Config, setup_environment

def test_sell_function():
    """매도 기능 테스트"""
    
    # 환경 설정
    if not setup_environment():
        print("❌ 환경 설정 실패")
        return
    
    # API 연결
    try:
        upbit = pyupbit.Upbit(Config.UPBIT_ACCESS_KEY, Config.UPBIT_SECRET_KEY)
        print("✅ API 연결 성공")
    except Exception as e:
        print(f"❌ API 연결 실패: {e}")
        return
    
    print("\n" + "="*50)
    print("매도 기능 테스트")
    print("="*50)
    
    # 전체 잔고 확인
    try:
        balances = upbit.get_balances()
        print(f"\n📊 전체 잔고:")
        
        for balance in balances:
            currency = balance['currency']
            amount = float(balance['balance'])
            locked = float(balance['locked'])
            
            if amount > 0 or locked > 0:
                if currency == 'KRW':
                    print(f"   {currency}: {amount:,.0f} (잠김: {locked:,.0f})")
                else:
                    # 현재가 조회
                    ticker = f"KRW-{currency}"
                    try:
                        current_price = pyupbit.get_current_price(ticker)
                        if current_price:
                            value = amount * current_price
                            print(f"   {currency}: {amount:.8f} (가치: {value:,.0f} KRW, 현재가: {current_price:,.0f})")
                        else:
                            print(f"   {currency}: {amount:.8f} (현재가 조회 불가)")
                    except:
                        print(f"   {currency}: {amount:.8f} (현재가 조회 실패)")
        
        # 코인 잔고가 있는지 확인
        coin_balances = [b for b in balances if b['currency'] != 'KRW' and float(b['balance']) > 0]
        
        if not coin_balances:
            print("\n⚠️ 매도 테스트를 위한 코인 잔고가 없습니다.")
            return
        
        # 첫 번째 코인으로 매도 테스트 시뮬레이션
        test_balance = coin_balances[0]
        currency = test_balance['currency']
        amount = float(test_balance['balance'])
        ticker = f"KRW-{currency}"
        
        print(f"\n🎯 매도 테스트 대상: {ticker}")
        print(f"   보유 수량: {amount:.8f}")
        
        # 현재가 확인
        current_price = pyupbit.get_current_price(ticker)
        if current_price:
            print(f"   현재가: {current_price:,.0f} KRW")
            print(f"   예상 매도 금액: {amount * current_price:,.0f} KRW")
            
            # 매도 주문 테스트 (실제로는 실행하지 않음)
            print(f"\n🔄 매도 주문 테스트 (시뮬레이션):")
            print(f"   upbit.sell_market_order('{ticker}', {amount:.8f})")
            print(f"   ↳ 이 명령으로 실제 매도가 실행됩니다.")
            
            # 실제 매도를 원한다면 아래 주석을 해제하세요
            """
            try:
                print("⚠️ 실제 매도 주문을 실행합니다. 5초 후 진행...")
                import time
                time.sleep(5)
                
                order = upbit.sell_market_order(ticker, amount)
                if order and 'uuid' in order:
                    print(f"✅ 매도 주문 성공! Order ID: {order['uuid']}")
                else:
                    print(f"❌ 매도 주문 실패: {order}")
            except Exception as e:
                print(f"❌ 매도 주문 오류: {e}")
            """
        else:
            print(f"❌ {ticker} 현재가 조회 실패")
            
    except Exception as e:
        print(f"❌ 잔고 조회 실패: {e}")

def test_sell_conditions():
    """매도 조건 테스트"""
    print("\n" + "="*50)
    print("매도 조건 테스트")
    print("="*50)
    
    # 가상의 포지션으로 테스트
    import datetime
    
    test_position = {
        'entry_price': 1000,
        'tp': 1050,  # 5% 익절
        'sl': 950,   # 5% 손절  
        'entry_time': datetime.datetime.now() - datetime.timedelta(hours=25)  # 25시간 전 진입
    }
    
    test_prices = [1060, 940, 1020]  # TP도달, SL도달, 시간매도
    
    for i, current_price in enumerate(test_prices):
        print(f"\n테스트 {i+1}: 현재가 {current_price}")
        
        pnl_pct = (current_price / test_position['entry_price'] - 1) * 100
        hold_time = (datetime.datetime.now() - test_position['entry_time']).total_seconds() / 3600
        
        print(f"   PnL: {pnl_pct:+.2f}%")
        print(f"   보유시간: {hold_time:.1f}시간")
        
        should_sell = False
        reason = ""
        
        if current_price >= test_position['tp']:
            should_sell = True
            reason = "Take Profit"
        elif current_price <= test_position['sl']:
            should_sell = True
            reason = "Stop Loss"
        elif hold_time > 24 and pnl_pct > 0:
            should_sell = True
            reason = "Time Exit (Profit)"
        
        if should_sell:
            print(f"   ✅ 매도 조건 달성: {reason}")
        else:
            print(f"   ❌ 매도 조건 미달성")

if __name__ == "__main__":
    print("🔬 매도 기능 종합 테스트")
    test_sell_function()
    test_sell_conditions()