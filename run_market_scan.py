# -*- coding: utf-8 -*-
"""
시장 스캔 도구 - 거래량 상위 코인 분석
"""
import sys
from market_analyzer import MarketAnalyzer
import json
from datetime import datetime

def main():
    print("=" * 80)
    print("UPBIT MARKET SCANNER - Real-time Volume & Liquidity Analysis")
    print("=" * 80)
    
    analyzer = MarketAnalyzer()
    
    # 명령행 인수로 최소 거래량 설정 가능
    min_volume = 5_000_000_000  # 기본 50억원
    if len(sys.argv) > 1:
        min_volume = float(sys.argv[1]) * 1_000_000_000
        print(f"Custom minimum volume: {min_volume/1e9:.1f}B KRW")
    
    try:
        # 1. 전체 시장 스캔
        top_coins = analyzer.get_top_coins(top_n=15, min_volume=min_volume)
        
        # 2. 카테고리별 분석
        print("\n" + "=" * 60)
        print("DETAILED CATEGORY ANALYSIS")
        print("=" * 60)
        
        categories = {
            'high_volume': [],      # 초고거래량 (100억 이상)
            'high_volatility': [],  # 고변동성 (10% 이상)
            'trending_up': [],      # 상승 추세
            'liquid_stable': [],    # 유동성 좋은 안정 코인
            'breakout_candidates': [] # 돌파 후보
        }
        
        for ticker, analysis in top_coins:
            # 카테고리 분류
            if analysis['volume_krw_1d'] > 100_000_000_000:
                categories['high_volume'].append(ticker)
            
            if analysis['volatility_1d'] > 10:
                categories['high_volatility'].append(ticker)
            
            if analysis['returns_7d'] > 5 and analysis['trend_score'] > 0:
                categories['trending_up'].append(ticker)
            
            if (analysis['volume_krw_7d_avg'] > 20_000_000_000 and 
                analysis['volatility_1d'] < 7 and analysis['avg_spread'] < 2):
                categories['liquid_stable'].append(ticker)
            
            if (analysis['returns_1d'] > 3 and analysis['volume_krw_1d'] > 
                analysis['volume_krw_7d_avg'] * 1.5):
                categories['breakout_candidates'].append(ticker)
        
        # 카테고리별 출력
        for category, coins in categories.items():
            if coins:
                print(f"\n📊 {category.upper().replace('_', ' ')}: {', '.join(coins[:5])}")
        
        # 3. 포트폴리오 추천
        print("\n" + "=" * 60)
        print("PORTFOLIO RECOMMENDATIONS")
        print("=" * 60)
        
        portfolios = {
            '보수적 (100만원 이하)': analyzer.get_trading_recommendations(500_000),
            '균형 (100만-1000만원)': analyzer.get_trading_recommendations(3_000_000),
            '공격적 (1000만원 이상)': analyzer.get_trading_recommendations(15_000_000)
        }
        
        for portfolio_name, recommendations in portfolios.items():
            print(f"\n💰 {portfolio_name}:")
            for risk_level, coins in recommendations.items():
                if coins:
                    print(f"  {risk_level}: {', '.join(coins[:3])}")
        
        # 4. 실시간 시장 상태
        print("\n" + "=" * 60)
        print("MARKET HEAT MAP")
        print("=" * 60)
        
        total_volume = sum(analysis['volume_krw_1d'] for _, analysis in top_coins)
        avg_volatility = sum(analysis['volatility_1d'] for _, analysis in top_coins) / len(top_coins)
        
        up_coins = sum(1 for _, analysis in top_coins if analysis['returns_1d'] > 0)
        down_coins = len(top_coins) - up_coins
        
        print(f"📈 Market Status:")
        print(f"  Total Volume (Top 15): {total_volume/1e12:.2f}T KRW")
        print(f"  Average Volatility: {avg_volatility:.2f}%")
        print(f"  Up vs Down: {up_coins} : {down_coins}")
        
        # 시장 상태 판단
        if avg_volatility > 8:
            market_state = "🔥 HIGH VOLATILITY"
        elif avg_volatility > 5:
            market_state = "📊 NORMAL"
        else:
            market_state = "😴 LOW VOLATILITY"
        
        print(f"  Market State: {market_state}")
        
        # 5. JSON 결과 저장
        results = {
            'timestamp': datetime.now().isoformat(),
            'top_coins': {ticker: analysis for ticker, analysis in top_coins},
            'categories': categories,
            'portfolios': portfolios,
            'market_summary': {
                'total_volume': total_volume,
                'avg_volatility': avg_volatility,
                'up_coins': up_coins,
                'down_coins': down_coins,
                'market_state': market_state
            }
        }
        
        with open('market_scan_results.json', 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n💾 Results saved to market_scan_results.json")
        
        # 6. 트레이딩 시그널
        print("\n" + "=" * 60)
        print("TRADING SIGNALS")
        print("=" * 60)
        
        signals = []
        for ticker, analysis in top_coins[:10]:
            signal_strength = 0
            reasons = []
            
            # 거래량 증가
            if analysis['volume_krw_1d'] > analysis['volume_krw_7d_avg'] * 1.5:
                signal_strength += 2
                reasons.append("Volume Surge")
            
            # 상승 추세
            if analysis['returns_1d'] > 2 and analysis['trend_score'] > 0:
                signal_strength += 2
                reasons.append("Uptrend")
            
            # 적정 변동성
            if 3 < analysis['volatility_1d'] < 8:
                signal_strength += 1
                reasons.append("Good Volatility")
            
            # 유동성
            if analysis['avg_spread'] < 1.5 and analysis['activity_ratio'] > 80:
                signal_strength += 1
                reasons.append("High Liquidity")
            
            if signal_strength >= 3:
                signals.append({
                    'ticker': ticker,
                    'strength': signal_strength,
                    'reasons': reasons,
                    'price': analysis['price']
                })
        
        if signals:
            print("🎯 Strong Trading Signals:")
            for signal in sorted(signals, key=lambda x: x['strength'], reverse=True)[:5]:
                print(f"  {signal['ticker']}: {signal['strength']}/6 - {', '.join(signal['reasons'])}")
        else:
            print("⚠️ No strong trading signals at the moment")
        
        print("\n" + "=" * 80)
        print("Scan completed! Use 'python auto_trader.py' to start automated trading.")
        print("=" * 80)
        
    except KeyboardInterrupt:
        print("\n\nScan interrupted by user")
    except Exception as e:
        print(f"\nError during market scan: {e}")

if __name__ == "__main__":
    print("Usage: python run_market_scan.py [min_volume_in_billions]")
    print("Example: python run_market_scan.py 10  # 최소 100억원 거래량")
    print()
    main()