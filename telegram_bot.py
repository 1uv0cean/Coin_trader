# -*- coding: utf-8 -*-
"""
텔레그램 알림 시스템
"""
import requests
import json
import datetime
from typing import Optional

class TelegramNotifier:
    def __init__(self, bot_token: str = None, chat_id: str = None):
        """
        텔레그램 알림 초기화
        
        Args:
            bot_token: 텔레그램 봇 토큰
            chat_id: 채팅방 ID
        """
        self.bot_token = None
        self.chat_id = None
        
        if bot_token and chat_id:
            self.bot_token = bot_token
            self.chat_id = chat_id
            self.enabled = True
        else:
            self.enabled = self._load_config()
        
        if self.enabled and self.bot_token:
            self.base_url = f"https://api.telegram.org/bot{self.bot_token}/"
        else:
            self.base_url = None
    
    def _load_config(self):
        """설정에서 봇 정보 로드 (.env 우선, txt 파일 폴백)"""
        try:
            # .env에서 로드 시도
            from config import Config
            if Config.TELEGRAM_BOT_TOKEN and Config.TELEGRAM_CHAT_ID:
                self.bot_token = Config.TELEGRAM_BOT_TOKEN
                self.chat_id = Config.TELEGRAM_CHAT_ID
                return True
        except ImportError:
            pass
        
        # 기존 txt 파일에서 로드 (호환성)
        try:
            with open("telegram_config.txt", "r") as f:
                lines = f.readlines()
                if len(lines) >= 2:
                    self.bot_token = lines[0].strip()
                    self.chat_id = lines[1].strip()
                    return True
                else:
                    print("⚠️ telegram_config.txt 파일이 올바르지 않습니다")
                    return False
        except FileNotFoundError:
            print("⚠️ 텔레그램 설정을 찾을 수 없습니다")
            print("📱 텔레그램 알림을 사용하려면:")
            print("   방법 1: .env 파일에 TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID 설정")
            print("   방법 2: telegram_config.txt 파일 생성 (첫째줄: 토큰, 둘째줄: Chat ID)")
            return False
        except Exception as e:
            print(f"❌ 텔레그램 설정 로드 오류: {e}")
            return False
    
    def send_message(self, message: str, parse_mode: str = "Markdown") -> bool:
        """메시지 전송"""
        if not self.enabled:
            return False
        
        try:
            url = self.base_url + "sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": parse_mode
            }
            
            response = requests.post(url, data=data, timeout=10)
            
            if response.status_code == 200:
                return True
            else:
                print(f"❌ 텔레그램 전송 실패: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ 텔레그램 전송 오류: {e}")
            return False
    
    def send_trade_alert(self, action: str, ticker: str, price: float, 
                        qty: float, strategy: str, tp: float = None, sl: float = None):
        """거래 알림 전송"""
        if not self.enabled:
            return
        
        # 이모지 선택
        if action == "BUY":
            emoji = "🟢"
        elif action in ["TP", "SELL"]:
            emoji = "💰"
        elif action == "SL":
            emoji = "🔴"
        else:
            emoji = "📊"
        
        # 메시지 구성
        coin_name = ticker.replace("KRW-", "")
        time_str = datetime.datetime.now().strftime("%H:%M:%S")
        
        message = f"{emoji} *{action} SIGNAL* {emoji}\n\n"
        message += f"🪙 *Coin*: `{coin_name}`\n"
        message += f"💵 *Price*: `{price:,.0f}` KRW\n"
        message += f"📊 *Quantity*: `{qty:.8f}`\n"
        message += f"💡 *Strategy*: `{strategy}`\n"
        
        if tp and sl:
            message += f"🎯 *TP*: `{tp:,.0f}` KRW\n"
            message += f"🛑 *SL*: `{sl:,.0f}` KRW\n"
        
        message += f"⏰ *Time*: `{time_str}`\n"
        
        # 거래 금액 계산
        trade_amount = price * qty
        message += f"💳 *Amount*: `{trade_amount:,.0f}` KRW"
        
        self.send_message(message)
    
    def send_exit_alert(self, exit_type: str, ticker: str, exit_price: float, 
                       entry_price: float, qty: float, pnl: float, pnl_pct: float):
        """청산 알림 전송"""
        if not self.enabled:
            return
        
        # 수익/손실에 따른 이모지
        if pnl > 0:
            emoji = "🎉"
            status = "PROFIT"
        else:
            emoji = "😞"
            status = "LOSS"
        
        coin_name = ticker.replace("KRW-", "")
        time_str = datetime.datetime.now().strftime("%H:%M:%S")
        
        message = f"{emoji} *{exit_type} - {status}* {emoji}\n\n"
        message += f"🪙 *Coin*: `{coin_name}`\n"
        message += f"📈 *Entry*: `{entry_price:,.0f}` KRW\n"
        message += f"📉 *Exit*: `{exit_price:,.0f}` KRW\n"
        message += f"📊 *Quantity*: `{qty:.8f}`\n"
        message += f"💰 *PnL*: `{pnl:+,.0f}` KRW (`{pnl_pct:+.2f}%`)\n"
        message += f"⏰ *Time*: `{time_str}`"
        
        self.send_message(message)
    
    def send_market_alert(self, stage: int, stage_name: str, ticker: str, 
                         rsi: float, volume_ratio: float, momentum: float):
        """시장 상태 알림"""
        if not self.enabled:
            return
        
        # 단계별 이모지
        stage_emojis = {
            0: "🔴", 1: "🟠", 2: "🟡", 3: "🟡", 4: "⚪",
            5: "⚪", 6: "🟢", 7: "🟢", 8: "🟢", 9: "🔥"
        }
        
        emoji = stage_emojis.get(stage, "📊")
        coin_name = ticker.replace("KRW-", "")
        time_str = datetime.datetime.now().strftime("%H:%M:%S")
        
        message = f"{emoji} *MARKET UPDATE* {emoji}\n\n"
        message += f"🪙 *Coin*: `{coin_name}`\n"
        message += f"📊 *Stage*: `{stage}` - {stage_name}\n"
        message += f"📈 *RSI*: `{rsi:.1f}`\n"
        message += f"📊 *Volume*: `{volume_ratio:.2f}x`\n"
        message += f"🚀 *Momentum*: `{momentum:+.2f}%`\n"
        message += f"⏰ *Time*: `{time_str}`"
        
        # 중요한 단계에서만 전송 (0-2, 7-9)
        if stage <= 2 or stage >= 7:
            self.send_message(message)
    
    def send_risk_alert(self, alert_type: str, message: str, balance: float = None):
        """리스크 경고 알림"""
        if not self.enabled:
            return
        
        time_str = datetime.datetime.now().strftime("%H:%M:%S")
        
        alert_msg = f"⚠️ *RISK ALERT* ⚠️\n\n"
        alert_msg += f"🔸 *Type*: `{alert_type}`\n"
        alert_msg += f"📝 *Message*: `{message}`\n"
        
        if balance:
            alert_msg += f"💰 *Balance*: `{balance:,.0f}` KRW\n"
        
        alert_msg += f"⏰ *Time*: `{time_str}`"
        
        self.send_message(alert_msg)
    
    def send_daily_summary(self, total_trades: int, winning_trades: int, 
                          losing_trades: int, total_pnl: float, win_rate: float):
        """일일 요약 알림"""
        if not self.enabled:
            return
        
        if total_pnl > 0:
            emoji = "📈"
            status = "PROFITABLE DAY"
        elif total_pnl < 0:
            emoji = "📉"
            status = "LOSS DAY"
        else:
            emoji = "➖"
            status = "BREAK EVEN"
        
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        
        message = f"{emoji} *DAILY SUMMARY* {emoji}\n\n"
        message += f"📅 *Date*: `{date_str}`\n"
        message += f"📊 *Status*: `{status}`\n\n"
        message += f"🔢 *Total Trades*: `{total_trades}`\n"
        message += f"✅ *Wins*: `{winning_trades}`\n"
        message += f"❌ *Losses*: `{losing_trades}`\n"
        message += f"📊 *Win Rate*: `{win_rate:.1f}%`\n"
        message += f"💰 *Total PnL*: `{total_pnl:+,.0f}` KRW"
        
        self.send_message(message)
    
    def send_startup_message(self, tickers: list, balance: float):
        """시작 메시지"""
        if not self.enabled or balance is None:
            return
        
        time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        coins = ", ".join([t.replace("KRW-", "") for t in tickers]) if tickers else "TBD"
        
        message = f"🤖 *AUTO TRADING STARTED* 🤖\n\n"
        message += f"⏰ *Start Time*: `{time_str}`\n"
        message += f"💰 *Current Balance*: `{balance:,.0f}` KRW\n"
        message += f"🪙 *Trading Coins*: `{coins}`\n"
        message += f"📊 *Strategy*: `10-Stage Adaptive`\n\n"
        message += f"🎯 Ready for automated trading! 🚀"
        
        self.send_message(message)
    
    def test_connection(self):
        """연결 테스트"""
        if not self.enabled:
            print("❌ 텔레그램 설정이 올바르지 않습니다")
            return False
        
        test_msg = f"🧪 *TEST MESSAGE* 🧪\n\n"
        test_msg += f"⏰ Time: `{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n"
        test_msg += f"✅ Telegram bot is working correctly!"
        
        success = self.send_message(test_msg)
        
        if success:
            print("✅ 텔레그램 연결 테스트 성공!")
        else:
            print("❌ 텔레그램 연결 테스트 실패!")
        
        return success

def setup_telegram():
    """텔레그램 봇 설정 가이드"""
    print("\n" + "="*60)
    print("TELEGRAM BOT SETUP GUIDE")
    print("="*60)
    print("1. 텔레그램에서 @BotFather 검색")
    print("2. /newbot 명령어 입력")
    print("3. 봇 이름과 username 설정")
    print("4. 받은 Bot Token을 복사")
    print("5. 봇과 채팅방 생성 후 메시지 전송")
    print("6. https://api.telegram.org/bot<TOKEN>/getUpdates 접속")
    print("7. chat id 확인")
    print("8. telegram_config.txt 파일 생성:")
    print("   첫째줄: Bot Token")
    print("   둘째줄: Chat ID")
    print("="*60)

if __name__ == "__main__":
    # 설정 가이드 출력
    setup_telegram()
    
    # 연결 테스트
    print("\n텔레그램 연결을 테스트합니다...")
    notifier = TelegramNotifier()
    
    if notifier.enabled:
        notifier.test_connection()
    else:
        print("❌ 설정을 완료한 후 다시 시도해주세요")