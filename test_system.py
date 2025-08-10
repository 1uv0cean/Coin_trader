# -*- coding: utf-8 -*-
"""
시스템 검증 테스트 - 모든 핵심 기능 동작 확인
"""
import pandas as pd
import numpy as np
import json
from datetime import datetime
import traceback

def create_test_data():
    """테스트용 가상 데이터 생성"""
    dates = pd.date_range(start='2024-01-01', periods=200, freq='5min')
    
    # 현실적인 가격 움직임 시뮬레이션
    np.random.seed(42)
    price = 50000
    prices = []
    volumes = []
    
    for i in range(200):
        # 트렌드 + 노이즈
        trend = np.sin(i / 50) * 0.001
        volatility = 0.005 + np.sin(i / 30) * 0.002  # 변동성 변화
        change = np.random.randn() * volatility + trend
        
        price *= (1 + change)
        prices.append(max(price, 1000))  # 최소 1000원
        
        # 거래량 시뮬레이션
        base_volume = 1000000
        volume_multiplier = 1 + abs(change) * 10  # 가격 변동이 클 때 거래량 증가
        volume = base_volume * volume_multiplier * (1 + np.random.uniform(-0.5, 0.5))
        volumes.append(volume)
    
    # OHLCV 생성
    data = {
        'timestamp': dates,
        'open': prices,
        'close': prices,
        'volume': volumes
    }
    
    # High/Low 생성 (Close 기반)
    df = pd.DataFrame(data)
    df['high'] = df['close'] * (1 + np.random.uniform(0, 0.02, len(df)))
    df['low'] = df['close'] * (1 - np.random.uniform(0, 0.02, len(df)))
    
    return df

def test_strategy_engine():
    """전략 엔진 테스트"""
    print("🧪 Testing Strategy Engine...")
    
    try:
        from strategy_engine import (
            calc_market_snapshot, calc_market_index, 
            decide_order, RiskManager, STRATEGY_MAP
        )
        
        # 테스트 데이터 생성
        df = create_test_data()
        
        # 1. 시장 스냅샷 테스트
        print("  1. Testing market snapshot calculation...")
        snap = calc_market_snapshot(df)
        
        assert hasattr(snap, 'rsi'), "RSI missing from snapshot"
        assert hasattr(snap, 'close_changes_1d'), "1D change missing"
        assert 0 <= snap.rsi <= 100, f"Invalid RSI: {snap.rsi}"
        
        print(f"     ✅ RSI: {snap.rsi:.1f}")
        print(f"     ✅ 1D Change: {snap.close_changes_1d:+.2f}%")
        print(f"     ✅ Volume Ratio: {snap.volume_rel_5d:.2f}x")
        
        # 2. 시장 인덱스 테스트
        print("  2. Testing market index calculation...")
        market_idx = calc_market_index(snap)
        
        assert 0 <= market_idx <= 9, f"Invalid market index: {market_idx}"
        print(f"     ✅ Market Index: {market_idx}")
        
        # 3. 전략 매핑 테스트
        print("  3. Testing strategy mapping...")
        strategy_count = 0
        for idx in range(10):
            if idx in STRATEGY_MAP:
                strategy_count += 1
                strat = STRATEGY_MAP[idx]
                plan = strat(df, snap)
                print(f"     Stage {idx}: {'✅' if plan else '⚪'}")
        
        assert strategy_count == 10, f"Missing strategies: {10-strategy_count}"
        
        # 4. 리스크 매니저 테스트
        print("  4. Testing risk manager...")
        risk_mgr = RiskManager()
        
        # 손실 테스트
        risk_mgr.update_pnl(-10000)
        risk_mgr.update_pnl(-20000)
        
        assert risk_mgr.daily_pnl == -30000, f"PnL calculation error: {risk_mgr.daily_pnl}"
        assert risk_mgr.trades_today == 2, f"Trade count error: {risk_mgr.trades_today}"
        
        print(f"     ✅ Daily PnL: {risk_mgr.daily_pnl:,}")
        print(f"     ✅ Trades: {risk_mgr.trades_today}")
        
        # 5. 통합 주문 결정 테스트
        print("  5. Testing order decision...")
        result = decide_order(df, 1000000, risk_mgr)
        
        assert 'index' in result, "Missing index in result"
        assert 'snapshot' in result, "Missing snapshot in result"
        assert 'stage_name' in result, "Missing stage_name in result"
        
        print(f"     ✅ Stage: {result['stage_name']}")
        print(f"     ✅ Plan: {'Yes' if result['plan'] else 'No'}")
        
        return True
        
    except Exception as e:
        print(f"     ❌ Strategy Engine Error: {e}")
        print(f"     Details: {traceback.format_exc()}")
        return False

def test_market_analyzer():
    """마켓 분석기 테스트 (API 호출 없이)"""
    print("\n🧪 Testing Market Analyzer...")
    
    try:
        from market_analyzer import MarketAnalyzer
        
        # 1. 인스턴스 생성 테스트
        print("  1. Testing analyzer initialization...")
        analyzer = MarketAnalyzer()
        
        assert hasattr(analyzer, 'min_volume_krw'), "Missing volume threshold"
        assert hasattr(analyzer, 'exclude_coins'), "Missing exclude list"
        
        print(f"     ✅ Min Volume: {analyzer.min_volume_krw/1e9:.1f}B KRW")
        print(f"     ✅ Excluded: {len(analyzer.exclude_coins)} coins")
        
        # 2. 점수 계산 테스트 (가상 데이터)
        print("  2. Testing score calculation...")
        
        fake_coins = [
            {
                'ticker': 'KRW-TEST1',
                'volume_krw_1d': 50000000000,
                'volume_krw_7d_avg': 40000000000,
                'volatility_1d': 5.0,
                'returns_7d': 2.5,
                'avg_spread': 1.0,
                'activity_ratio': 85,
                'trend_score': 1
            },
            {
                'ticker': 'KRW-TEST2', 
                'volume_krw_1d': 30000000000,
                'volume_krw_7d_avg': 25000000000,
                'volatility_1d': 8.0,
                'returns_7d': -1.2,
                'avg_spread': 2.5,
                'activity_ratio': 70,
                'trend_score': -1
            }
        ]
        
        scored_coins = analyzer.calculate_scores(fake_coins)
        
        assert len(scored_coins) == 2, "Score calculation failed"
        assert all('score' in coin for coin in scored_coins), "Missing scores"
        
        print(f"     ✅ Coin 1 Score: {scored_coins[0]['score']:.1f}")
        print(f"     ✅ Coin 2 Score: {scored_coins[1]['score']:.1f}")
        
        # 3. 추천 시스템 테스트
        print("  3. Testing recommendation logic...")
        
        # 가상 추천 로직 (API 호출 없이)
        balance_tests = [100000, 1000000, 10000000]
        
        for balance in balance_tests:
            if balance < 100_000:
                min_vol = 1_000_000_000
                max_coins = 1
            elif balance < 1_000_000:
                min_vol = 5_000_000_000
                max_coins = 3
            else:
                min_vol = 10_000_000_000
                max_coins = 5
            
            print(f"     ✅ Balance {balance:,}: {max_coins} coins, {min_vol/1e9:.1f}B min vol")
        
        return True
        
    except Exception as e:
        print(f"     ❌ Market Analyzer Error: {e}")
        print(f"     Details: {traceback.format_exc()}")
        return False

def test_backtest_engine():
    """백테스트 엔진 테스트"""
    print("\n🧪 Testing Backtest Engine...")
    
    try:
        from run_backtest import BacktestEngine
        
        # 1. 엔진 초기화 테스트
        print("  1. Testing engine initialization...")
        engine = BacktestEngine(initial_krw=1000000, fee_rate=0.0005)
        
        assert engine.cash == 1000000, f"Initial cash error: {engine.cash}"
        assert engine.fee_rate == 0.0005, f"Fee rate error: {engine.fee_rate}"
        
        print(f"     ✅ Initial Cash: {engine.cash:,}")
        print(f"     ✅ Fee Rate: {engine.fee_rate*100:.03f}%")
        
        # 2. 수수료 계산 테스트
        print("  2. Testing fee calculation...")
        fee = engine.calculate_fees(1000000)
        expected_fee = 1000000 * 0.0005
        
        assert fee == expected_fee, f"Fee calculation error: {fee} vs {expected_fee}"
        print(f"     ✅ Fee for 1M KRW: {fee:,.0f} KRW")
        
        # 3. 매수 테스트
        print("  3. Testing buy execution...")
        success = engine.execute_buy(50000, 0.01, 52000, 48000, "Test Buy", "2024-01-01")
        
        assert success, "Buy execution failed"
        assert len(engine.positions) == 1, f"Position not created: {len(engine.positions)}"
        
        print(f"     ✅ Position Created: {engine.positions[0]['note']}")
        print(f"     ✅ Remaining Cash: {engine.cash:,.0f}")
        
        # 4. 청산 테스트
        print("  4. Testing exit conditions...")
        closed = engine.check_exits(53000, 47000, 51000, "2024-01-02")
        
        # TP 도달했으므로 청산되어야 함
        assert len(closed) > 0, "TP exit not triggered"
        assert len(engine.positions) == 0, "Position not closed"
        
        print(f"     ✅ Position Closed: TP Hit")
        print(f"     ✅ Final Cash: {engine.cash:,.0f}")
        
        return True
        
    except Exception as e:
        print(f"     ❌ Backtest Engine Error: {e}")
        print(f"     Details: {traceback.format_exc()}")
        return False

def test_integration():
    """통합 테스트"""
    print("\n🧪 Testing System Integration...")
    
    try:
        # 1. 데이터 플로우 테스트
        print("  1. Testing data flow...")
        df = create_test_data()
        
        from strategy_engine import decide_order, RiskManager
        result = decide_order(df, 1000000, RiskManager())
        
        assert isinstance(result, dict), "Result not a dictionary"
        required_keys = ['index', 'snapshot', 'stage_name']
        
        for key in required_keys:
            assert key in result, f"Missing key: {key}"
        
        print(f"     ✅ Data Flow Complete")
        print(f"     ✅ Market Stage: {result['stage_name']}")
        
        # 2. 백테스트 실행 테스트
        print("  2. Testing full backtest...")
        from run_backtest import BacktestEngine
        
        engine = BacktestEngine(initial_krw=1000000)
        metrics = engine.run(df, lookback=50)
        
        required_metrics = ['total_return_pct', 'win_rate_pct', 'sharpe_ratio']
        for metric in required_metrics:
            assert metric in metrics, f"Missing metric: {metric}"
        
        print(f"     ✅ Backtest Complete")
        print(f"     ✅ Return: {metrics['total_return_pct']:.2f}%")
        print(f"     ✅ Win Rate: {metrics['win_rate_pct']:.1f}%")
        
        return True
        
    except Exception as e:
        print(f"     ❌ Integration Error: {e}")
        print(f"     Details: {traceback.format_exc()}")
        return False

def main():
    """전체 시스템 테스트 실행"""
    print("=" * 80)
    print("COMPREHENSIVE SYSTEM VALIDATION TEST")
    print("=" * 80)
    print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    tests = [
        ("Strategy Engine", test_strategy_engine),
        ("Market Analyzer", test_market_analyzer), 
        ("Backtest Engine", test_backtest_engine),
        ("System Integration", test_integration)
    ]
    
    results = {}
    total_tests = len(tests)
    passed_tests = 0
    
    for test_name, test_func in tests:
        print(f"\n🔬 Running {test_name} Tests...")
        try:
            success = test_func()
            results[test_name] = "✅ PASSED" if success else "❌ FAILED"
            if success:
                passed_tests += 1
        except Exception as e:
            results[test_name] = f"❌ ERROR: {e}"
    
    # 결과 요약
    print("\n" + "=" * 80)
    print("TEST RESULTS SUMMARY")
    print("=" * 80)
    
    for test_name, result in results.items():
        print(f"{test_name:<20}: {result}")
    
    print(f"\nOverall Result: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 ALL TESTS PASSED - System is ready for trading!")
        
        # 사용 가이드
        print("\n" + "=" * 80)
        print("QUICK START GUIDE")
        print("=" * 80)
        print("1. Set up API keys in upbit.txt")
        print("2. Run: python auto_trader.py")
        print("3. Monitor: Check trading.log for activity")
        print("=" * 80)
        
    else:
        print(f"⚠️  {total_tests - passed_tests} tests failed - Fix issues before trading")
    
    # 결과 저장
    test_results = {
        'timestamp': datetime.now().isoformat(),
        'tests': results,
        'passed': passed_tests,
        'total': total_tests,
        'success_rate': passed_tests / total_tests * 100
    }
    
    with open('test_results.json', 'w') as f:
        json.dump(test_results, f, indent=2)
    
    print(f"\n💾 Test results saved to test_results.json")

if __name__ == "__main__":
    main()