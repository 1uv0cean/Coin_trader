# 📱 텔레그램 알림 설정 가이드

## 🤖 1. 텔레그램 봇 생성

### 1-1. @BotFather 찾기
1. 텔레그램 앱에서 **@BotFather** 검색
2. 채팅 시작

### 1-2. 봇 생성
```
/newbot
```
- 봇 이름 입력: `나의 트레이딩 봇`
- 봇 username 입력: `my_trading_bot` (끝에 bot 필수)

### 1-3. Bot Token 복사
```
1234567890:ABCdefGHIjklMNOpqrsTUVwxyz1234567890
```
⬆️ 이런 형태의 토큰을 복사해두세요

## 💬 2. Chat ID 자동 획득 (**추천**)

### 🚀 방법 1: 자동 획득 도구 사용
```bash
python3 get_chat_id.py
```

1. Bot Token 입력
2. 텔레그램에서 봇과 채팅 (아무 메시지나 전송)
3. Enter 누르면 자동으로 Chat ID 확인 및 설정 완료!

### 🔧 방법 2: 수동으로 확인
1. 생성된 봇을 찾아서 채팅방 입장
2. `/start` 또는 아무 메시지나 전송
3. 웹 브라우저에서 접속:
```
https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
```
4. YOUR_BOT_TOKEN을 실제 토큰으로 교체
5. 결과에서 "chat"의 "id" 찾기:
```json
{
  "chat": {
    "id": 123456789,  ← 이 숫자가 Chat ID
    "first_name": "Your Name"
  }
}
```

## 📝 3. 설정 파일 생성

`telegram_config.txt` 파일을 생성하고 다음과 같이 입력:

```
1234567890:ABCdefGHIjklMNOpqrsTUVwxyz1234567890
123456789
```

- **첫째줄**: Bot Token
- **둘째줄**: Chat ID

## ✅ 4. 연결 테스트

```bash
python3 telegram_bot.py
```

성공시 텔레그램으로 테스트 메시지가 전송됩니다!

## 📊 5. 알림 종류

### 🟢 매수 알림
```
🟢 BUY SIGNAL 🟢

🪙 Coin: BTC
💵 Price: 52,000,000 KRW  
📊 Quantity: 0.00010000
💡 Strategy: Stage6: breakout
🎯 TP: 53,560,000 KRW
🛑 SL: 51,220,000 KRW
⏰ Time: 14:25:30
💳 Amount: 5,200,000 KRW
```

### 💰 청산 알림  
```
🎉 TP - PROFIT 🎉

🪙 Coin: BTC
📈 Entry: 52,000,000 KRW
📉 Exit: 53,560,000 KRW  
📊 Quantity: 0.00010000
💰 PnL: +156,000 KRW (+3.00%)
⏰ Time: 15:42:18
```

### 🔥 시장 상태 알림
```
🟢 MARKET UPDATE 🟢

🪙 Coin: BTC
📊 Stage: 8 - Strong Up
📈 RSI: 68.5
📊 Volume: 1.85x
🚀 Momentum: +5.42%
⏰ Time: 16:15:22
```

### ⚠️ 리스크 알림
```
⚠️ RISK ALERT ⚠️

🔸 Type: DAILY_LIMIT
📝 Message: Daily loss limit reached
💰 Balance: 950,000 KRW
⏰ Time: 18:30:45
```

## 🎯 완료!

이제 `python3 auto_trader.py` 실행하면 모든 거래가 텔레그램으로 실시간 알림됩니다! 🚀