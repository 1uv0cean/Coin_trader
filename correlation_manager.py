# -*- coding: utf-8 -*-
"""
코인 간 상관관계 분석 및 포트폴리오 리스크 관리
"""

import pandas as pd
import numpy as np
import pyupbit
from typing import List, Dict, Tuple
from datetime import datetime, timedelta

class CorrelationManager:
    def __init__(self, max_correlation=0.7, analysis_period=30):
        """
        상관관계 매니저 초기화
        
        Args:
            max_correlation: 허용 최대 상관관계 (0.7 = 70%)
            analysis_period: 분석 기간 (일)
        """
        self.max_correlation = max_correlation
        self.analysis_period = analysis_period
        self.correlation_matrix = None
        self.last_update = None
        self.price_data = {}
    
    def update_correlation_matrix(self, tickers: List[str]) -> bool:
        """상관관계 매트릭스 업데이트"""
        try:
            print(f"📊 Updating correlation matrix for {len(tickers)} tickers...")
            
            # 가격 데이터 수집
            price_data = {}
            for ticker in tickers:
                df = pyupbit.get_ohlcv(ticker, interval="day", count=self.analysis_period + 5)
                if df is not None and len(df) >= self.analysis_period:
                    price_data[ticker] = df['close'].pct_change().dropna()
                else:
                    print(f"⚠️ {ticker}: Insufficient data")
            
            if len(price_data) < 2:
                print("❌ Not enough data for correlation analysis")
                return False
            
            # 공통 날짜로 데이터 정렬
            common_dates = None
            for ticker, returns in price_data.items():
                if common_dates is None:
                    common_dates = set(returns.index)
                else:
                    common_dates = common_dates.intersection(set(returns.index))
            
            if len(common_dates) < self.analysis_period * 0.8:
                print("❌ Not enough common dates for reliable correlation")
                return False
            
            # 상관관계 매트릭스 계산
            aligned_returns = {}
            for ticker, returns in price_data.items():
                aligned_returns[ticker] = returns[returns.index.isin(common_dates)]
            
            returns_df = pd.DataFrame(aligned_returns)
            self.correlation_matrix = returns_df.corr()
            self.last_update = datetime.now()
            self.price_data = price_data
            
            print(f"✅ Correlation matrix updated successfully")
            self._print_correlation_summary()
            
            return True
            
        except Exception as e:
            print(f"❌ Error updating correlation matrix: {e}")
            return False
    
    def _print_correlation_summary(self):
        """상관관계 요약 출력"""
        if self.correlation_matrix is None:
            return
        
        print(f"\n📈 Correlation Analysis Summary (Top correlations):")
        print("-" * 50)
        
        # 상위 상관관계 페어 찾기
        correlations = []
        for i in range(len(self.correlation_matrix.index)):
            for j in range(i+1, len(self.correlation_matrix.columns)):
                ticker1 = self.correlation_matrix.index[i]
                ticker2 = self.correlation_matrix.columns[j]
                corr = self.correlation_matrix.iloc[i, j]
                if not np.isnan(corr):
                    correlations.append((ticker1, ticker2, corr))
        
        # 상관관계 순으로 정렬
        correlations.sort(key=lambda x: abs(x[2]), reverse=True)
        
        # 상위 5개 출력
        for i, (t1, t2, corr) in enumerate(correlations[:5]):
            status = "⚠️ HIGH" if abs(corr) > self.max_correlation else "✅ OK"
            print(f"{i+1}. {t1} - {t2}: {corr:+.3f} ({status})")
    
    def check_portfolio_correlation(self, current_tickers: List[str], 
                                  candidate_ticker: str) -> Dict:
        """포트폴리오 상관관계 체크"""
        if self.correlation_matrix is None:
            return {"allowed": True, "reason": "No correlation data"}
        
        if candidate_ticker not in self.correlation_matrix.index:
            return {"allowed": True, "reason": "No data for candidate ticker"}
        
        if not current_tickers:
            return {"allowed": True, "reason": "No current positions"}
        
        # 기존 포지션과의 상관관계 체크
        high_correlations = []
        for ticker in current_tickers:
            if ticker in self.correlation_matrix.index:
                corr = self.correlation_matrix.loc[candidate_ticker, ticker]
                if not np.isnan(corr) and abs(corr) > self.max_correlation:
                    high_correlations.append((ticker, corr))
        
        if high_correlations:
            reason = f"High correlation with: {', '.join([f'{t}({c:+.2f})' for t, c in high_correlations])}"
            return {
                "allowed": False, 
                "reason": reason,
                "correlations": high_correlations
            }
        
        return {"allowed": True, "reason": "Correlation within acceptable range"}
    
    def get_diversified_portfolio(self, candidate_tickers: List[str], 
                                max_positions: int = 3) -> List[str]:
        """분산된 포트폴리오 구성"""
        if self.correlation_matrix is None or len(candidate_tickers) <= max_positions:
            return candidate_tickers[:max_positions]
        
        # 유효한 티커들만 필터링
        valid_tickers = [t for t in candidate_tickers if t in self.correlation_matrix.index]
        
        if len(valid_tickers) <= max_positions:
            return valid_tickers
        
        # 그리디 알고리즘으로 분산 포트폴리오 구성
        selected = [valid_tickers[0]]  # 첫 번째 코인 선택
        
        for _ in range(max_positions - 1):
            best_candidate = None
            min_max_correlation = float('inf')
            
            for candidate in valid_tickers:
                if candidate in selected:
                    continue
                
                # 기존 선택된 코인들과의 최대 상관관계 계산
                max_corr = 0
                for selected_ticker in selected:
                    corr = abs(self.correlation_matrix.loc[candidate, selected_ticker])
                    if not np.isnan(corr):
                        max_corr = max(max_corr, corr)
                
                # 최대 상관관계가 가장 낮은 코인 선택
                if max_corr < min_max_correlation:
                    min_max_correlation = max_corr
                    best_candidate = candidate
            
            if best_candidate:
                selected.append(best_candidate)
            else:
                # 남은 코인들 중 아무거나 선택
                remaining = [t for t in valid_tickers if t not in selected]
                if remaining:
                    selected.append(remaining[0])
        
        print(f"\n🎯 Diversified Portfolio Selected:")
        for i, ticker in enumerate(selected, 1):
            avg_corr = self._get_average_correlation(ticker, selected)
            print(f"  {i}. {ticker} (Avg correlation: {avg_corr:.3f})")
        
        return selected
    
    def _get_average_correlation(self, ticker: str, portfolio: List[str]) -> float:
        """포트폴리오 내 평균 상관관계 계산"""
        if self.correlation_matrix is None:
            return 0.0
        
        correlations = []
        for other_ticker in portfolio:
            if other_ticker != ticker and other_ticker in self.correlation_matrix.index:
                corr = self.correlation_matrix.loc[ticker, other_ticker]
                if not np.isnan(corr):
                    correlations.append(abs(corr))
        
        return np.mean(correlations) if correlations else 0.0
    
    def get_portfolio_risk_metrics(self, tickers: List[str]) -> Dict:
        """포트폴리오 리스크 지표 계산"""
        if self.correlation_matrix is None or len(tickers) < 2:
            return {"avg_correlation": 0.0, "max_correlation": 0.0, "risk_score": "LOW"}
        
        correlations = []
        for i, ticker1 in enumerate(tickers):
            for ticker2 in tickers[i+1:]:
                if ticker1 in self.correlation_matrix.index and ticker2 in self.correlation_matrix.index:
                    corr = self.correlation_matrix.loc[ticker1, ticker2]
                    if not np.isnan(corr):
                        correlations.append(abs(corr))
        
        if not correlations:
            return {"avg_correlation": 0.0, "max_correlation": 0.0, "risk_score": "LOW"}
        
        avg_corr = np.mean(correlations)
        max_corr = np.max(correlations)
        
        # 리스크 스코어 계산
        if max_corr > 0.8:
            risk_score = "VERY HIGH"
        elif max_corr > 0.7:
            risk_score = "HIGH"
        elif max_corr > 0.5:
            risk_score = "MEDIUM"
        else:
            risk_score = "LOW"
        
        return {
            "avg_correlation": avg_corr,
            "max_correlation": max_corr,
            "risk_score": risk_score,
            "correlation_count": len(correlations)
        }
    
    def should_update_matrix(self) -> bool:
        """매트릭스 업데이트 필요 여부 확인"""
        if self.last_update is None:
            return True
        
        # 24시간마다 업데이트
        return (datetime.now() - self.last_update).seconds > 86400

def main():
    """테스트 실행"""
    # 테스트용 코인들
    test_tickers = ['KRW-BTC', 'KRW-ETH', 'KRW-XRP', 'KRW-ADA', 'KRW-DOT', 'KRW-LINK', 'KRW-LTC']
    
    # 상관관계 매니저 초기화
    corr_manager = CorrelationManager(max_correlation=0.7, analysis_period=30)
    
    # 상관관계 매트릭스 업데이트
    if corr_manager.update_correlation_matrix(test_tickers):
        
        # 분산 포트폴리오 구성
        diversified = corr_manager.get_diversified_portfolio(test_tickers, max_positions=3)
        
        # 포트폴리오 리스크 지표
        risk_metrics = corr_manager.get_portfolio_risk_metrics(diversified)
        
        print(f"\n🎯 Portfolio Risk Assessment:")
        print(f"Average Correlation: {risk_metrics['avg_correlation']:.3f}")
        print(f"Maximum Correlation: {risk_metrics['max_correlation']:.3f}")
        print(f"Risk Score: {risk_metrics['risk_score']}")

if __name__ == "__main__":
    main()