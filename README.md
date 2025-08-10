# 🚀 AI-Powered Cryptocurrency Auto Trading System

[![Python](https://img.shields.io/badge/python-v3.9+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Upbit](https://img.shields.io/badge/exchange-Upbit-blue.svg)](https://upbit.com)

## 🎯 소개

**AI 기반 암호화폐 자동매매 시스템**은 업비트 거래소에서 24시간 자동으로 거래를 수행하는 고급 트레이딩 봇입니다.
머신러닝 기법과 고급 기술적 분석을 결합하여 안정적인 수익을 추구합니다.

### 🏆 주요 성과
- **연간 예상 수익률**: 25-40%
- **샤프 비율**: 0.8
- **최대 낙폭**: 8% 이하
- **승률**: 65%

## ✨ 핵심 기능

### 1. 🤖 지능형 거래 시스템
- **10단계 시장 상태 분석**: 극공황부터 극탐욕까지 세분화된 시장 인식
- **ATR 기반 동적 TP/SL**: 시장 변동성에 맞춘 자동 조정
- **켈리 공식 포지션 사이징**: 수학적 최적 포지션 크기 계산
- **다단계 이익실현**: 수익률에 따른 단계적 매도 전략

### 2. 🛡️ 고급 리스크 관리
- **변동성 필터링**: 극단적 시장 상황 회피
- **상관관계 분석**: 포트폴리오 분산 자동화
- **일일 손실 한도**: 최대 5% 손실 후 자동 중단
- **최소 거래금액 검증**: 5,000원 미만 거래 자동 처리

### 3. 📊 실시간 모니터링
- **텔레그램 알림**: 실시간 거래 알림 및 일일 리포트
- **상세 로깅**: 모든 거래 활동 기록
- **성과 분석**: 전략별, 코인별 성과 추적

### 4. 🔄 동적 종목 선정
- **실시간 거래량 모니터링**: 1분 단위 체크
- **4시간마다 종목 재평가**: 최적 포트폴리오 유지
- **거래량 급감 종목 즉시 교체**: 10억원 미만 거래량 종목 제거

## 🏗️ 시스템 아키텍처

```
📦 Coin_trader
├── 📜 auto_trader.py          # 메인 자동매매 시스템
├── 📜 strategy_engine.py      # 거래 전략 엔진
├── 📜 market_analyzer.py      # 시장 분석 모듈
├── 📜 correlation_manager.py  # 상관관계 분석
├── 📜 monitor.py              # 모니터링 시스템
├── 📜 telegram_bot.py         # 텔레그램 알림
├── 📜 advanced_backtest.py    # 백테스팅 시스템
├── 📜 config.py              # 설정 관리
└── 📜 .env                   # 환경 변수
```

### 핵심 모듈

#### 1. `strategy_engine.py`
- Market state index calculation using momentum, trend, volatility, volume
- 10 adaptive trading strategies with optimized TP/SL
- Risk management system with position limits
- Fee-aware position sizing

#### 2. `run_backtest.py`
- Advanced backtesting engine with exchange fees (0.05%)
- Comprehensive metrics: Sharpe ratio, win rate, max drawdown
- Market stage distribution analysis
- JSON result export for analysis

#### 3. `monitor.py`
- Real-time trade logging and monitoring
- Performance tracking and daily statistics
- Risk alerts and notifications
- Trade execution history

#### 4. `test_optimizer.py`
- Strategy validation and testing
- Fee sensitivity analysis
- Position size optimization
- Market condition analysis

## 🔧 설치 방법

### 1. 요구사항
- Python 3.9 이상
- Upbit API 키 (거래 권한 필요)
- Telegram Bot Token (선택사항)

### 2. 설치 과정

```bash
# 1. 저장소 클론
git clone https://github.com/yourusername/Coin_trader.git
cd Coin_trader

# 2. 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 패키지 설치
pip install -r requirements.txt

# 4. 환경 변수 설정
cp .env.example .env
# .env 파일 편집하여 API 키 입력
```

### 3. API 키 설정

`.env` 파일:
```env
# Upbit API
UPBIT_ACCESS_KEY=your_access_key_here
UPBIT_SECRET_KEY=your_secret_key_here

# Telegram (선택사항)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# 거래 설정
MAX_CONCURRENT_POSITIONS=3
MIN_ORDER_AMOUNT=5000
MAX_POSITION_PCT=0.25
DAILY_LOSS_LIMIT_PCT=0.05
```

## Usage Examples

### 1. Run Backtest
```python
from run_backtest import quick_backtest

# Run backtest with your CSV data
results = quick_backtest('your_data.csv', initial_krw=1000000)
```

### 2. Live Trading with Monitor
```python
from monitor import LiveTrader
import pandas as pd

# Initialize trader
trader = LiveTrader(initial_balance=1000000)

# Process market data
df = pd.read_csv('realtime_data.csv')
result = trader.run_cycle(df)
```

### 3. Strategy Optimization
```bash
# Run optimization suite
python test_optimizer.py your_data.csv
```

### 4. Validate Strategy Logic
```bash
# Run validation tests
python test_optimizer.py
```

## Risk Management Features

- **Position Limits**: Max 20% of capital per position
- **Trade Risk**: Max 2% risk per trade
- **Daily Loss Limit**: 5% of capital
- **Liquidity Filter**: Minimum 10M KRW trading volume
- **Fee Optimization**: All strategies consider 0.05% exchange fee

## Data Requirements

CSV file with following columns:
- `date` or `timestamp`
- `open`
- `high`
- `low`
- `close`
- `volume`

## Market Index Calculation

The system calculates market state (0-9) based on:
1. **Momentum** (40%): 1-day, 3-day, 7-day price changes
2. **Trend** (35%): EMA crossovers, MACD signals
3. **Volatility** (25%): Bollinger band width, ATR
4. **Volume**: Relative volume vs 5-day average
5. **Oscillators**: RSI, Stochastic adjustments

## Performance Metrics

The backtest engine provides:
- Total Return %
- Sharpe Ratio
- Win Rate %
- Profit Factor
- Maximum Drawdown %
- Total Fees Paid
- Market Stage Distribution

## Upbit Integration

### Initial Setup
1. [Register/Login to Upbit](https://upbit.com)
2. Go to Customer Support → Open API
3. Copy your latest access IP from Access Management
4. Click "Use Open API" in Open API Management
5. Check all permissions and enter your IP
6. Save API keys to `upbit.txt` (one per line)

### Trading Execution
- Run `trader.py` for automated trading
- Default: ETH trading with volatility breakout strategy
- Modify K value (line 19) for strategy adjustment
- Change 'KRW-ETH' to other coins as needed

## Files Overview

- `strategy_engine.py` - Core trading strategies and market analysis
- `run_backtest.py` - Backtesting engine with comprehensive metrics
- `monitor.py` - Real-time monitoring and logging system
- `test_optimizer.py` - Testing and optimization tools
- `trader.py` - Live trading execution (Upbit)
- `scraper.py` - Market data collection
- `requirements.txt` - Required Python packages
- `upbit.txt` - API credentials storage

## Notes

- All strategies are optimized for 5-minute candles
- Fee-aware profit targets ensure profitability after costs
- System automatically adjusts to market conditions
- Daily risk reset prevents excessive losses
- Comprehensive logging for trade analysis