# -*- coding: utf-8 -*-
"""
환경변수 및 설정 관리
"""
import os
from dotenv import load_dotenv
from typing import Optional

# .env 파일 로드
load_dotenv()

class Config:
    """앱 설정 클래스"""
    
    # Upbit API 설정
    UPBIT_ACCESS_KEY: str = os.getenv('UPBIT_ACCESS_KEY', '')
    UPBIT_SECRET_KEY: str = os.getenv('UPBIT_SECRET_KEY', '')
    
    # 텔레그램 설정
    TELEGRAM_BOT_TOKEN: str = os.getenv('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_CHAT_ID: str = os.getenv('TELEGRAM_CHAT_ID', '')
    
    # 트레이딩 설정
    MAX_CONCURRENT_POSITIONS: int = int(os.getenv('MAX_CONCURRENT_POSITIONS', '3'))
    FEE_RATE: float = float(os.getenv('FEE_RATE', '0.0005'))
    MIN_ORDER_AMOUNT: float = float(os.getenv('MIN_ORDER_AMOUNT', '5500'))
    
    # 리스크 관리
    MAX_POSITION_PCT: float = float(os.getenv('MAX_POSITION_PCT', '0.20'))
    MAX_TRADE_RISK_PCT: float = float(os.getenv('MAX_TRADE_RISK_PCT', '0.02'))
    DAILY_LOSS_LIMIT_PCT: float = float(os.getenv('DAILY_LOSS_LIMIT_PCT', '0.05'))
    
    # 백테스트 설정
    BACKTEST_LOOKBACK: int = int(os.getenv('BACKTEST_LOOKBACK', '60'))
    SAVE_RESULTS: bool = os.getenv('SAVE_RESULTS', 'true').lower() == 'true'
    
    # 로깅 설정
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE: str = os.getenv('LOG_FILE', 'trading.log')
    
    @classmethod
    def validate_config(cls) -> tuple[bool, list[str]]:
        """설정 검증"""
        errors = []
        
        # 필수 설정 확인
        if not cls.UPBIT_ACCESS_KEY:
            errors.append("UPBIT_ACCESS_KEY가 설정되지 않았습니다")
        if not cls.UPBIT_SECRET_KEY:
            errors.append("UPBIT_SECRET_KEY가 설정되지 않았습니다")
        
        # 텔레그램 설정 (선택적)
        if cls.TELEGRAM_BOT_TOKEN and not cls.TELEGRAM_CHAT_ID:
            errors.append("TELEGRAM_BOT_TOKEN이 있지만 TELEGRAM_CHAT_ID가 없습니다")
        
        # 범위 검증
        if not (0.0 < cls.MAX_POSITION_PCT <= 1.0):
            errors.append("MAX_POSITION_PCT는 0과 1 사이의 값이어야 합니다")
        
        if not (0.0 < cls.MAX_TRADE_RISK_PCT <= 0.1):
            errors.append("MAX_TRADE_RISK_PCT는 0과 0.1 사이의 값이어야 합니다")
        
        if not (0.0 < cls.DAILY_LOSS_LIMIT_PCT <= 0.5):
            errors.append("DAILY_LOSS_LIMIT_PCT는 0과 0.5 사이의 값이어야 합니다")
        
        if cls.MIN_ORDER_AMOUNT < 5000:
            errors.append("MIN_ORDER_AMOUNT는 최소 5,000원 이상이어야 합니다")
        
        return len(errors) == 0, errors
    
    @classmethod
    def print_config(cls):
        """설정 출력 (민감한 정보 마스킹)"""
        print("=" * 60)
        print("CURRENT CONFIGURATION")
        print("=" * 60)
        
        # API 키 마스킹
        access_masked = cls.UPBIT_ACCESS_KEY[:8] + "*" * 20 if cls.UPBIT_ACCESS_KEY else "Not Set"
        secret_masked = cls.UPBIT_SECRET_KEY[:8] + "*" * 20 if cls.UPBIT_SECRET_KEY else "Not Set"
        token_masked = cls.TELEGRAM_BOT_TOKEN[:10] + "*" * 30 if cls.TELEGRAM_BOT_TOKEN else "Not Set"
        
        print(f"Upbit Access Key: {access_masked}")
        print(f"Upbit Secret Key: {secret_masked}")
        print(f"Telegram Token:   {token_masked}")
        print(f"Telegram Chat ID: {cls.TELEGRAM_CHAT_ID}")
        print()
        
        print(f"Max Positions:    {cls.MAX_CONCURRENT_POSITIONS}")
        print(f"Fee Rate:         {cls.FEE_RATE:.4f} ({cls.FEE_RATE*100:.2f}%)")
        print(f"Min Order:        {cls.MIN_ORDER_AMOUNT:,.0f} KRW")
        print()
        
        print(f"Max Position:     {cls.MAX_POSITION_PCT:.1%}")
        print(f"Max Trade Risk:   {cls.MAX_TRADE_RISK_PCT:.1%}")
        print(f"Daily Loss Limit: {cls.DAILY_LOSS_LIMIT_PCT:.1%}")
        print()
        
        print(f"Backtest Lookback: {cls.BACKTEST_LOOKBACK}")
        print(f"Save Results:      {cls.SAVE_RESULTS}")
        print(f"Log Level:         {cls.LOG_LEVEL}")
        print("=" * 60)

def load_legacy_config():
    """기존 txt 파일에서 설정 로드 (호환성)"""
    config_updates = {}
    
    # upbit.txt 파일 확인
    try:
        with open("upbit.txt", "r") as f:
            lines = f.readlines()
            if len(lines) >= 2:
                config_updates['UPBIT_ACCESS_KEY'] = lines[0].strip()
                config_updates['UPBIT_SECRET_KEY'] = lines[1].strip()
                print("✅ upbit.txt에서 API 키를 로드했습니다")
    except FileNotFoundError:
        pass
    
    # telegram_config.txt 파일 확인
    try:
        with open("telegram_config.txt", "r") as f:
            lines = f.readlines()
            if len(lines) >= 2:
                config_updates['TELEGRAM_BOT_TOKEN'] = lines[0].strip()
                config_updates['TELEGRAM_CHAT_ID'] = lines[1].strip()
                print("✅ telegram_config.txt에서 텔레그램 설정을 로드했습니다")
    except FileNotFoundError:
        pass
    
    # 환경변수 업데이트
    for key, value in config_updates.items():
        if value and not os.getenv(key):
            os.environ[key] = value
    
    return len(config_updates) > 0

def setup_environment():
    """환경 설정 초기화"""
    print("🔧 환경 설정을 확인하는 중...")
    
    # .env 파일 존재 확인
    if not os.path.exists('.env'):
        print("⚠️ .env 파일이 없습니다")
        
        # 기존 txt 파일에서 로드 시도
        if load_legacy_config():
            print("📄 기존 설정 파일에서 로드했습니다")
            
            # .env 파일 생성 제안
            create_env = input("🤔 .env 파일로 통합할까요? (y/n): ").lower()
            if create_env == 'y':
                create_env_from_legacy()
        else:
            print("❌ 설정 파일이 없습니다")
            print("💡 .env.example을 참고하여 .env 파일을 생성하세요")
            return False
    
    # 설정 검증
    is_valid, errors = Config.validate_config()
    
    if not is_valid:
        print("❌ 설정 오류:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    print("✅ 환경 설정이 완료되었습니다!")
    return True

def create_env_from_legacy():
    """기존 txt 파일들을 .env로 변환"""
    env_content = []
    
    # 기본 템플릿
    with open('.env.example', 'r') as f:
        template = f.read()
    
    env_content.append("# 자동 생성된 .env 파일")
    env_content.append("# " + "=" * 50)
    env_content.append("")
    
    # Upbit 설정
    try:
        with open("upbit.txt", "r") as f:
            lines = f.readlines()
            if len(lines) >= 2:
                env_content.append("# Upbit API 설정")
                env_content.append(f"UPBIT_ACCESS_KEY={lines[0].strip()}")
                env_content.append(f"UPBIT_SECRET_KEY={lines[1].strip()}")
                env_content.append("")
    except FileNotFoundError:
        env_content.append("# Upbit API 설정")
        env_content.append("UPBIT_ACCESS_KEY=your_upbit_access_key_here")
        env_content.append("UPBIT_SECRET_KEY=your_upbit_secret_key_here")
        env_content.append("")
    
    # 텔레그램 설정
    try:
        with open("telegram_config.txt", "r") as f:
            lines = f.readlines()
            if len(lines) >= 2:
                env_content.append("# 텔레그램 봇 설정")
                env_content.append(f"TELEGRAM_BOT_TOKEN={lines[0].strip()}")
                env_content.append(f"TELEGRAM_CHAT_ID={lines[1].strip()}")
                env_content.append("")
    except FileNotFoundError:
        env_content.append("# 텔레그램 봇 설정")
        env_content.append("TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here")
        env_content.append("TELEGRAM_CHAT_ID=your_telegram_chat_id_here")
        env_content.append("")
    
    # 나머지 기본 설정 추가
    env_content.append("# 트레이딩 설정")
    env_content.append("MAX_CONCURRENT_POSITIONS=3")
    env_content.append("FEE_RATE=0.0005")
    env_content.append("MIN_ORDER_AMOUNT=5500")
    env_content.append("")
    
    env_content.append("# 리스크 관리")
    env_content.append("MAX_POSITION_PCT=0.20")
    env_content.append("MAX_TRADE_RISK_PCT=0.02")
    env_content.append("DAILY_LOSS_LIMIT_PCT=0.05")
    env_content.append("")
    
    env_content.append("# 기타 설정")
    env_content.append("BACKTEST_LOOKBACK=60")
    env_content.append("SAVE_RESULTS=true")
    env_content.append("LOG_LEVEL=INFO")
    env_content.append("LOG_FILE=trading.log")
    
    # .env 파일 생성
    with open('.env', 'w') as f:
        f.write('\n'.join(env_content))
    
    print("✅ .env 파일이 생성되었습니다!")
    print("📁 기존 txt 파일들은 백업용으로 유지됩니다")

if __name__ == "__main__":
    if setup_environment():
        Config.print_config()
    else:
        print("\n💡 설정 가이드:")
        print("1. .env.example을 .env로 복사")
        print("2. .env 파일을 편집하여 실제 값 입력")
        print("3. python3 config.py로 검증")