# -*- coding: utf-8 -*-
"""
텔레그램 Chat ID 자동 획득 도구
"""
import requests
import json

def get_chat_id_from_token(bot_token):
    """봇 토큰으로 Chat ID 자동 획득"""
    
    print("=" * 60)
    print("TELEGRAM CHAT ID 자동 획득 도구")
    print("=" * 60)
    
    # 1. 먼저 봇과 채팅해야 함을 안내
    print("🤖 단계:")
    print("1. 텔레그램에서 생성한 봇을 찾으세요")
    print("2. 봇과 채팅을 시작하고 아무 메시지나 보내세요 (예: 안녕)")
    print("3. Enter 키를 눌러 Chat ID를 확인하세요")
    input("\n봇에게 메시지를 보낸 후 Enter를 누르세요...")
    
    # 2. Updates 가져오기
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    
    try:
        print("\n🔍 Chat ID를 찾는 중...")
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            print(f"❌ API 요청 실패: {response.status_code}")
            print(f"응답: {response.text}")
            return None
        
        data = response.json()
        
        if not data.get('ok'):
            print(f"❌ 텔레그램 API 오류: {data}")
            return None
        
        results = data.get('result', [])
        
        if not results:
            print("❌ 메시지가 없습니다!")
            print("💡 해결방법:")
            print("   1. 텔레그램에서 봇을 찾으세요")
            print("   2. /start 또는 아무 메시지를 보내세요")
            print("   3. 다시 이 스크립트를 실행하세요")
            return None
        
        # 3. Chat ID들 찾기
        chat_ids = set()
        
        for update in results:
            if 'message' in update:
                chat = update['message'].get('chat', {})
                chat_id = chat.get('id')
                if chat_id:
                    chat_ids.add(str(chat_id))
                    print(f"✅ 발견된 Chat ID: {chat_id}")
                    print(f"   사용자: {chat.get('first_name', '')} {chat.get('last_name', '')}")
                    print(f"   유형: {chat.get('type', 'private')}")
        
        if chat_ids:
            if len(chat_ids) == 1:
                chat_id = list(chat_ids)[0]
                print(f"\n🎉 Chat ID 획득 성공: {chat_id}")
                
                # 4. 자동으로 설정 파일 생성
                try:
                    with open('telegram_config.txt', 'w') as f:
                        f.write(f"{bot_token}\n")
                        f.write(f"{chat_id}\n")
                    
                    print(f"\n📝 telegram_config.txt 파일이 자동으로 생성되었습니다!")
                    print("✅ 이제 텔레그램 알림을 사용할 수 있습니다!")
                    
                    # 5. 테스트 메시지 전송
                    test_message = "🎉 Chat ID 설정 완료!\n\n✅ 텔레그램 알림이 정상적으로 작동합니다."
                    
                    test_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                    test_data = {
                        'chat_id': chat_id,
                        'text': test_message
                    }
                    
                    test_response = requests.post(test_url, data=test_data)
                    
                    if test_response.status_code == 200:
                        print("📱 테스트 메시지가 전송되었습니다!")
                    else:
                        print("⚠️ 테스트 메시지 전송에 실패했지만 설정은 완료되었습니다.")
                    
                    return chat_id
                    
                except Exception as e:
                    print(f"⚠️ 설정 파일 생성 오류: {e}")
                    print(f"수동으로 telegram_config.txt를 생성하고 다음을 입력하세요:")
                    print(f"첫째줄: {bot_token}")
                    print(f"둘째줄: {chat_id}")
                    return chat_id
            else:
                print(f"\n🤔 여러 개의 Chat ID가 발견되었습니다:")
                for i, cid in enumerate(chat_ids, 1):
                    print(f"   {i}. {cid}")
                print("\n가장 최근의 것을 사용하는 것을 권장합니다.")
                return list(chat_ids)[-1]
        else:
            print("❌ Chat ID를 찾을 수 없습니다.")
            return None
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        print("\n💡 문제 해결:")
        print("1. 인터넷 연결 확인")
        print("2. Bot Token이 올바른지 확인")
        print("3. 봇에게 메시지를 보냈는지 확인")
        return None

def main():
    print("텔레그램 Chat ID 자동 획득 도구")
    print("=" * 40)
    
    # 토큰 입력
    bot_token = input("🤖 Bot Token을 입력하세요: ").strip()
    
    if not bot_token:
        print("❌ Bot Token이 입력되지 않았습니다.")
        return
    
    if len(bot_token) < 40:
        print("❌ Bot Token이 너무 짧습니다. 올바른 토큰을 입력하세요.")
        print("예시: 1234567890:ABCdefGHIjklMNOpqrsTUVwxyz1234567890")
        return
    
    # Chat ID 획득
    chat_id = get_chat_id_from_token(bot_token)
    
    if chat_id:
        print("\n" + "=" * 60)
        print("🎉 설정 완료! 이제 자동매매를 시작할 수 있습니다!")
        print("=" * 60)
        print("다음 명령어로 자동매매를 시작하세요:")
        print("python3 auto_trader.py")
        print("=" * 60)
    else:
        print("\n❌ Chat ID 획득에 실패했습니다.")
        print("\n📞 도움이 필요하시면:")
        print("1. 봇이 제대로 생성되었는지 확인")
        print("2. 봇과 채팅을 시작했는지 확인")
        print("3. Bot Token이 올바른지 확인")

if __name__ == "__main__":
    main()