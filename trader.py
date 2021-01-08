import pyupbit
import pprint
import time
import datetime

# API 이용 로그인
f = open("upbit.txt")
lines = f.readlines()
access = lines[0].strip()   # access key
secret = lines[1].strip()   # secret key
f.close()
upbit = pyupbit.Upbit(access, secret)   #class instance, object

def cal_target(ticker):
    df=pyupbit.get_ohlcv(ticker,"day")
    yesterday = df.iloc[-2]
    today = df.iloc[-1]
    yesterday_range = yesterday['high'] - yesterday['low']
    target = today['open'] + yesterday_range * 0.3
    return target

target = cal_target("KRW-ETH")
op_mode = False # 거래 여부
hold = False # 코인 보유 여부

# 잔고 조회
eth_balance = upbit.get_balance("KRW-ETH")
eth_price = pyupbit.get_current_price("KRW-ETH")
while True:
    now = datetime.datetime.now()

    # 매도 시도
    if now.hour == 8 and now.minute == 59 and 50 <= now.second <= 59:
        if op_mode is True and hold is True :
            eth_balance = upbit.get_balance("KRW-ETH")
            upbit.sell_market_order("KRW-ETH", eth_balance)
            hold = False
        op_mode = False
        time.sleep(10)

    # 09:00:00 목표가 갱신
    if now.hour == 9 and now.minute == 0 and 20 <= now.second <=30:
        target = cal_target("KRW-ETH")
        op_mode=True
        time.sleep(10)
    
    price = pyupbit.get_current_price("KRW-ETH")

    # 매초마다 조건을 확인한 후 매수 시도
    if op_mode is True and hold is False and price >= target and price is not None:
        # 매수
        krw_balance = upbit.get_balance("KRW")
        upbit.buy_market_order("KRW-ETH",krw_balance)
        hold = True

    #상태 출력
    print(f"현재 시간: {now} 목표가: {target} 현재가: {price} 보유상태: {hold} 동작상태: {op_mode}")
    time.sleep(1)

    
