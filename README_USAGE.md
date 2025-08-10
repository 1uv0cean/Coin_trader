# 트레이딩 시스템 사용 가이드

## 📁 파일 구조 및 용도

### ✅ 핵심 파일 (새로운 시스템)

#### 1. **auto_trader.py** - 🌟 메인 자동매매

```bash
python auto_trader.py
```

- **완전 자동 매매** - 24시간 무인 운영
- 잔고 자동 분석 및 분배
- 거래량 상위 코인 자동 선택
- 10단계 시장 분석 기반 매매

#### 2. **strategy_engine.py** - 전략 엔진

- 시장 상태 0-9 단계 계산
- 10개 적응형 전략
- 기술적 지표 계산
- 리스크 관리 시스템

#### 3. **run_backtest.py** - 백테스트

```python
from run_backtest import quick_backtest
results = quick_backtest('data.csv')
```

- 과거 데이터로 전략 검증
- 수수료 포함 수익률 계산

#### 4. **monitor.py** - 모니터링

- 실시간 거래 로깅
- 성과 추적
- 리스크 알림

### ⚠️ 구버전 파일 (선택적 사용)

#### **trader.py** - 단순 변동성 돌파 전략

- 구버전 단일 코인 트레이더
- ETH 전용 변동성 돌파
- **auto_trader.py로 대체됨**

#### **scraper.py** - 마켓 정보 조회

- Upbit 상장 코인 목록 확인용
- 단순 정보 조회 도구

## 🚀 실행 방법

### 1. 최신 자동매매 시작

```bash
# 설치
pip install -r requirements.txt

# API 키 설정 (upbit.txt)
첫째줄: Access Key
둘째줄: Secret Key

# 실행
python auto_trader.py
```

### 2. 기능별 사용

**백테스트만 실행:**

```bash
python run_backtest.py
```

**최적화 테스트:**

```bash
python test_optimizer.py your_data.csv
```

**모니터링만:**

```bash
python monitor.py
```

## 📊 시스템 비교

| 구분     | trader.py (구버전) | auto_trader.py (신버전) |
| -------- | ------------------ | ----------------------- |
| 전략     | 변동성 돌파 1개    | 10단계 적응형 전략      |
| 코인     | ETH 고정           | 자동 선택/다중 코인     |
| 리스크   | 기본적             | 고급 리스크 관리        |
| 모니터링 | 콘솔 출력          | 로깅 + 알림             |
| 백테스트 | 없음               | 통합 지원               |
| 수수료   | 미고려             | 0.05% 반영              |

## 💡 추천 사용법

### 초보자

```bash
# 자동으로 모든 것을 처리
python auto_trader.py
```

### 중급자

```python
# 특정 코인 지정
from auto_trader import FullAutoTrader

trader = FullAutoTrader(
    tickers=['KRW-BTC', 'KRW-ETH'],
    max_coins=2
)
trader.run()
```

### 고급자

```python
# 백테스트 후 실매매
from run_backtest import BacktestEngine

# 1. 백테스트
engine = BacktestEngine()
results = engine.run(df)

# 2. 결과 확인 후 실매매
if results['sharpe_ratio'] > 1.5:
    import auto_trader
    auto_trader.main()
```

## ❓ FAQ

**Q: trader.py를 삭제해도 되나요?**
A: 네, auto_trader.py가 모든 기능을 포함합니다.

**Q: scraper.py는 언제 사용하나요?**
A: 상장 코인 목록 확인시에만 필요합니다.

**Q: 어떤 파일을 실행해야 하나요?**
A: `python auto_trader.py` 하나만 실행하면 됩니다.
