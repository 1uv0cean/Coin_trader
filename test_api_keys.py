#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pyupbit
import sys
from config import Config, setup_environment

def test_api_keys():
    """Test if API keys are working"""
    print("🔧 Testing API keys...")
    
    if not setup_environment():
        print("❌ Environment setup failed")
        return False
    
    try:
        # Test API connection
        upbit = pyupbit.Upbit(Config.UPBIT_ACCESS_KEY, Config.UPBIT_SECRET_KEY)
        
        # Test balance retrieval
        print("📊 Testing balance retrieval...")
        krw_balance = upbit.get_balance("KRW")
        
        if krw_balance is None:
            print("❌ API 키가 유효하지 않거나 잔고를 가져올 수 없습니다.")
            print("💡 다음을 확인하세요:")
            print("   1. API 키가 올바른지")
            print("   2. API 키에 거래 권한이 있는지")
            print("   3. IP가 허용 목록에 있는지")
            return False
        
        print(f"✅ API 연결 성공! KRW 잔고: {krw_balance:,.0f} KRW")
        
        # Test market data
        print("📈 Testing market data retrieval...")
        tickers = pyupbit.get_tickers(fiat="KRW")
        if tickers:
            print(f"✅ 마켓 데이터 조회 성공! {len(tickers)} 개 코인 발견")
            
            # Test individual ticker
            test_ticker = "KRW-BTC"
            df = pyupbit.get_ohlcv(test_ticker, interval="minute1", count=10)
            if df is not None and not df.empty:
                print(f"✅ {test_ticker} OHLCV 데이터 조회 성공!")
                print(f"   DataFrame shape: {df.shape}")
                print(f"   Columns: {list(df.columns)}")
            else:
                print(f"❌ {test_ticker} OHLCV 데이터 조회 실패")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ API 테스트 중 오류 발생: {e}")
        print(f"   Error type: {type(e).__name__}")
        return False

if __name__ == "__main__":
    success = test_api_keys()
    sys.exit(0 if success else 1)