# -*- coding: utf-8 -*-
import pyupbit
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
from typing import List, Dict, Tuple

class MarketAnalyzer:
    """시장 분석 및 최적 코인 선택"""
    
    def __init__(self):
        self.min_volume_krw = 10_000_000_000  # 최소 일일 거래대금 100억원
        self.min_market_cap = 50_000_000_000  # 최소 시가총액 500억원
        self.exclude_coins = [
            'KRW-USDT', 'KRW-USDC', 'KRW-BUSD', 'KRW-DAI',  # 스테이블 코인
            'KRW-WEMIX', 'KRW-BORA',  # 게임 코인 (변동성 높음)
        ]
        self.cache = {}
        self.cache_time = {}
        
    def get_all_tickers(self) -> List[str]:
        """모든 KRW 마켓 코인 목록"""
        try:
            tickers = pyupbit.get_tickers(fiat="KRW")
            # 제외 목록 필터링
            tickers = [t for t in tickers if t not in self.exclude_coins]
            print(f"Total {len(tickers)} KRW pairs found")
            return tickers
        except Exception as e:
            print(f"Error getting tickers: {e}")
            return []
    
    def analyze_coin(self, ticker: str) -> Dict:
        """개별 코인 분석"""
        try:
            # 캐시 확인 (5분)
            if ticker in self.cache:
                if time.time() - self.cache_time[ticker] < 300:
                    return self.cache[ticker]
            
            # 일봉 데이터
            df_day = pyupbit.get_ohlcv(ticker, interval="day", count=30)
            if df_day is None or len(df_day) < 7:
                return None
            
            # 5분봉 데이터
            df_5min = pyupbit.get_ohlcv(ticker, interval="minute1", count=288)
            if df_5min is None or len(df_5min) < 100:
                return None
            
            current_price = df_day['close'].iloc[-1]
            
            # 거래량 분석
            volume_krw_1d = df_day['volume'].iloc[-1] * current_price
            volume_krw_7d_avg = (df_day['volume'][-7:] * df_day['close'][-7:]).mean()
            volume_krw_30d_avg = (df_day['volume'] * df_day['close']).mean()
            
            # 변동성 분석
            volatility_1d = df_5min['close'].pct_change().std() * np.sqrt(288) * 100
            volatility_7d = df_day['close'][-7:].pct_change().std() * np.sqrt(252) * 100
            
            # 추세 분석
            returns_1d = (df_day['close'].iloc[-1] / df_day['close'].iloc[-2] - 1) * 100
            returns_7d = (df_day['close'].iloc[-1] / df_day['close'].iloc[-8] - 1) * 100
            returns_30d = (df_day['close'].iloc[-1] / df_day['close'].iloc[0] - 1) * 100
            
            # 기술적 지표
            ma7 = df_day['close'][-7:].mean()
            ma30 = df_day['close'].mean()
            
            # 유동성 점수 (거래 활발도)
            spread = (df_5min['high'] - df_5min['low']) / df_5min['close']
            avg_spread = spread.mean() * 100
            
            # 거래 빈도 (5분봉에서 가격 변화가 있는 캔들 비율)
            price_changes = df_5min['close'].diff() != 0
            activity_ratio = price_changes.sum() / len(price_changes) * 100
            
            result = {
                'ticker': ticker,
                'price': current_price,
                'volume_krw_1d': volume_krw_1d,
                'volume_krw_7d_avg': volume_krw_7d_avg,
                'volume_krw_30d_avg': volume_krw_30d_avg,
                'volatility_1d': volatility_1d,
                'volatility_7d': volatility_7d,
                'returns_1d': returns_1d,
                'returns_7d': returns_7d,
                'returns_30d': returns_30d,
                'ma7': ma7,
                'ma30': ma30,
                'trend_score': 1 if current_price > ma7 > ma30 else -1,
                'avg_spread': avg_spread,
                'activity_ratio': activity_ratio,
                'score': 0  # 종합 점수 (나중에 계산)
            }
            
            # 캐시 저장
            self.cache[ticker] = result
            self.cache_time[ticker] = time.time()
            
            return result
            
        except Exception as e:
            print(f"Error analyzing {ticker}: {e}")
            return None
    
    def calculate_scores(self, coins: List[Dict]) -> List[Dict]:
        """각 코인에 종합 점수 부여"""
        if not coins:
            return []
        
        df = pd.DataFrame(coins)
        
        # 각 지표별 순위 계산 (높을수록 좋음)
        df['volume_rank'] = df['volume_krw_1d'].rank(pct=True)
        df['liquidity_rank'] = df['volume_krw_7d_avg'].rank(pct=True)
        df['activity_rank'] = df['activity_ratio'].rank(pct=True)
        
        # 적정 변동성 (너무 높거나 낮지 않음)
        df['volatility_optimal'] = 1 - abs(df['volatility_1d'] - 5) / 10
        df['volatility_optimal'] = df['volatility_optimal'].clip(0, 1)
        
        # 스프레드는 낮을수록 좋음
        df['spread_rank'] = 1 - df['avg_spread'].rank(pct=True)
        
        # 추세 점수
        df['trend_rank'] = (df['returns_7d'] > 0).astype(int) * 0.5 + \
                          (df['trend_score'] > 0).astype(int) * 0.5
        
        # 종합 점수 계산 (가중치 적용)
        df['score'] = (
            df['volume_rank'] * 0.30 +        # 거래량 30%
            df['liquidity_rank'] * 0.20 +     # 유동성 20%
            df['activity_rank'] * 0.15 +      # 활동성 15%
            df['volatility_optimal'] * 0.15 + # 변동성 15%
            df['spread_rank'] * 0.10 +        # 스프레드 10%
            df['trend_rank'] * 0.10           # 추세 10%
        ) * 100
        
        # 결과 정렬
        df = df.sort_values('score', ascending=False)
        
        return df.to_dict('records')
    
    def get_top_coins(self, top_n: int = 10, min_volume: float = None) -> List[Tuple[str, Dict]]:
        """거래량 상위 코인 선택"""
        print(f"\n{'='*60}")
        print(f"Market Analysis - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        
        if min_volume is None:
            min_volume = self.min_volume_krw
        
        # 모든 코인 가져오기
        all_tickers = self.get_all_tickers()
        
        # 각 코인 분석
        analyzed_coins = []
        print(f"\nAnalyzing {len(all_tickers)} coins...")
        
        for i, ticker in enumerate(all_tickers):
            if i % 10 == 0:
                print(f"  Progress: {i}/{len(all_tickers)}")
            
            analysis = self.analyze_coin(ticker)
            if analysis and analysis['volume_krw_1d'] >= min_volume:
                analyzed_coins.append(analysis)
            
            time.sleep(0.1)  # API 제한 방지
        
        print(f"\nFound {len(analyzed_coins)} coins with volume > {min_volume/1e9:.1f}B KRW")
        
        # 점수 계산 및 정렬
        scored_coins = self.calculate_scores(analyzed_coins)
        
        # 상위 N개 선택
        top_coins = scored_coins[:top_n]
        
        print(f"\n📊 Top {top_n} Coins by Score:")
        print(f"{'Rank':<5} {'Ticker':<12} {'Price':<12} {'Volume(B)':<10} {'1D%':<8} {'Score':<8}")
        print("-" * 60)
        
        for i, coin in enumerate(top_coins, 1):
            print(f"{i:<5} {coin['ticker']:<12} {coin['price']:>11,.0f} "
                  f"{coin['volume_krw_1d']/1e9:>9.1f} {coin['returns_1d']:>7.2f}% "
                  f"{coin['score']:>7.1f}")
        
        return [(coin['ticker'], coin) for coin in top_coins]
    
    def get_trading_recommendations(self, balance: float) -> Dict:
        """잔고에 따른 거래 추천"""
        # 잔고가 None이거나 0인 경우 기본값 사용
        if balance is None or balance <= 0:
            balance = 1_000_000  # 기본 100만원
        
        # 잔고에 따라 최소 거래량 조정
        if balance < 100_000:
            min_volume = 1_000_000_000  # 10억원
            max_coins = 1
        elif balance < 1_000_000:
            min_volume = 5_000_000_000  # 50억원
            max_coins = 3
        else:
            min_volume = 10_000_000_000  # 100억원
            max_coins = 5
        
        # 상위 코인 선택
        top_coins = self.get_top_coins(top_n=max_coins*2, min_volume=min_volume)
        
        # 추천 구성
        recommendations = {
            'aggressive': [],  # 공격적 (높은 변동성)
            'balanced': [],    # 균형 (중간)
            'conservative': [] # 보수적 (낮은 변동성)
        }
        
        for ticker, analysis in top_coins:
            if analysis['volatility_1d'] > 7:
                recommendations['aggressive'].append(ticker)
            elif analysis['volatility_1d'] < 3:
                recommendations['conservative'].append(ticker)
            else:
                recommendations['balanced'].append(ticker)
        
        # 각 카테고리 최대 개수 제한
        for key in recommendations:
            recommendations[key] = recommendations[key][:max_coins]
        
        print(f"\n💡 Trading Recommendations (Balance: {balance:,.0f} KRW):")
        print(f"  Aggressive: {', '.join(recommendations['aggressive'])}")
        print(f"  Balanced: {', '.join(recommendations['balanced'])}")
        print(f"  Conservative: {', '.join(recommendations['conservative'])}")
        
        return recommendations

def update_auto_trader():
    """auto_trader.py를 업데이트하여 MarketAnalyzer 사용"""
    print("\n🔄 Updating auto_trader.py to use MarketAnalyzer...")
    
    analyzer = MarketAnalyzer()
    
    # 상위 10개 코인 분석
    top_coins = analyzer.get_top_coins(top_n=10)
    
    # 거래 추천
    recommendations = analyzer.get_trading_recommendations(balance=1_000_000)
    
    print(f"\n✅ Analysis Complete!")
    print(f"Recommended coins for auto trading:")
    
    # 균형잡힌 포트폴리오 구성
    selected = []
    if recommendations['balanced']:
        selected.extend(recommendations['balanced'][:2])
    if recommendations['aggressive']:
        selected.extend(recommendations['aggressive'][:1])
    if len(selected) < 3 and recommendations['conservative']:
        selected.extend(recommendations['conservative'][:1])
    
    print(f"\nFinal Selection: {', '.join(selected)}")
    
    return selected

if __name__ == "__main__":
    # 독립 실행시 시장 분석
    analyzer = MarketAnalyzer()
    
    # 상위 코인 분석
    top_coins = analyzer.get_top_coins(top_n=10, min_volume=5_000_000_000)
    
    # 거래 추천
    print("\n" + "="*60)
    recommendations = analyzer.get_trading_recommendations(balance=1_000_000)
    print("="*60)