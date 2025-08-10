# 🚀 통합 설정 가이드 (.env 방식)

## ✅ **개선된 설정 시스템**

모든 설정을 `.env` 파일 하나로 통합! 더 안전하고 관리하기 쉬워졌습니다.

### 📁 **기존 방식 vs 새로운 방식**

| 기존 | 새로운 방식 |
|------|-------------|
| `upbit.txt` | `.env` (UPBIT_ACCESS_KEY) |
| `telegram_config.txt` | `.env` (TELEGRAM_BOT_TOKEN) |
| 코드에 하드코딩 | `.env` (설정 분리) |

## 🔧 **설정 방법**

### 1. .env 파일 생성

```bash
# .env.example을 복사
cp .env.example .env
```

### 2. .env 파일 편집

```bash
# Upbit API 설정
UPBIT_ACCESS_KEY=your_actual_upbit_access_key_here
UPBIT_SECRET_KEY=your_actual_upbit_secret_key_here

# 텔레그램 봇 설정  
TELEGRAM_BOT_TOKEN=your_actual_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_actual_telegram_chat_id_here

# 트레이딩 설정 (필요시 조정)
MAX_CONCURRENT_POSITIONS=3
FEE_RATE=0.0005
MIN_ORDER_AMOUNT=5500

# 리스크 관리 (필요시 조정)
MAX_POSITION_PCT=0.20
MAX_TRADE_RISK_PCT=0.02
DAILY_LOSS_LIMIT_PCT=0.05
```

### 3. 설정 검증

```bash
python3 config.py
```

성공시 이런 화면이 나옵니다:
```
✅ 환경 설정이 완료되었습니다!
============================================================
CURRENT CONFIGURATION
============================================================
Upbit Access Key: y4ExDLzZ********************
Telegram Token:   7018525781******************************
Max Positions:    3
Fee Rate:         0.0005 (0.05%)
Min Order:        5,500 KRW
============================================================
```

## 🔄 **기존 파일 자동 변환**

기존 txt 파일들이 있다면 자동으로 .env로 변환됩니다:

```bash
python3 config.py
```

- `upbit.txt` → `.env`의 UPBIT_* 설정
- `telegram_config.txt` → `.env`의 TELEGRAM_* 설정
- 기존 파일들은 백업용으로 유지됩니다

## 🎯 **장점**

### ✅ **보안 강화**
- `.env` 파일은 `.gitignore`에 포함 (Git에 업로드 안 됨)
- API 키 노출 위험 최소화

### ✅ **관리 편의성**
- 모든 설정이 한 곳에
- 주석으로 설명 포함
- 타입 검증 자동화

### ✅ **유연성**
- 환경별 다른 설정 가능
- 런타임에 설정 변경 없이 재시작만으로 적용

### ✅ **호환성**
- 기존 txt 파일도 계속 지원
- 점진적 마이그레이션 가능

## 🚀 **실행**

```bash
# 1. 설정 확인
python3 config.py

# 2. 자동매매 시작
python3 auto_trader.py

# 3. 시장 분석
python3 run_market_scan.py
```

## ⚙️ **고급 설정**

### 리스크 관리 조정
```env
MAX_POSITION_PCT=0.15        # 포지션당 최대 15%
MAX_TRADE_RISK_PCT=0.01      # 거래당 최대 1% 리스크  
DAILY_LOSS_LIMIT_PCT=0.03    # 일일 최대 3% 손실
```

### 거래 설정 조정
```env
MAX_CONCURRENT_POSITIONS=5   # 최대 5개 코인 동시 거래
MIN_ORDER_AMOUNT=10000       # 최소 주문 금액 1만원  
FEE_RATE=0.0005             # 거래소 수수료 0.05%
```

### 💰 **실제 잔고 자동 사용**
- ✅ **더 이상 INITIAL_BALANCE 설정 불필요!**
- 🔄 **실시간 KRW 잔고 자동 조회**
- 🎯 **보유 코인도 자동 인식하여 관리**
- 💡 **실제 가용 자금으로 안전하게 거래**

## 🔐 **보안 주의사항**

1. **절대 .env 파일을 공유하지 마세요**
2. **Git에 업로드하지 마세요** (자동으로 제외됨)
3. **API 키는 읽기 전용 권한만 부여**
4. **정기적으로 API 키 갱신**

## 🎉 **완료!**

이제 하나의 `.env` 파일로 모든 설정을 깔끔하게 관리할 수 있습니다! 🎯