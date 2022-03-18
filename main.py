import os
from os.path import join, dirname
from time import sleep
from dotenv import load_dotenv
import schedule
import sys
import threading
from binance.enums import *
from binance.exceptions import BinanceAPIException


load_dotenv(verbose=True)

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

api_key = os.environ.get("KEY")
api_secret = os.environ.get("SECRET")

from binance import Client, ThreadedWebsocketManager, ThreadedDepthCacheManager
client = Client(api_key, api_secret) #,tld='us') #,testnet=True) # clientの作成　testnet=True にてtest実行が可能

help = 'このプログラムはbinanceにアクセスし、情報取得及び指値注文を行うための学習用プログラムです\n \
以下のコマンドを受け付けます\n \
help : このヘルプを表示\n \
quit : プログラムを終了する\n \
info : 口座関係情報を出力する(10分に1回、自動的に出力されます)\n \
order: 注文をする\n'



def background():
    while True:
        schedule.run_pending()
        sleep(1)


# now threading1 runs regardless of user input
threading1 = threading.Thread(target=background)
threading1.daemon = True
threading1.start()



# 3.注文キューの受付をする
# 	- 注文条件 : 過去10分の最安値で買、最高値で売のストップリミット注文
# 	- 注文方法 : 指値注文
# 	- 通貨ペア : TUSD/BUSD
# 	- 注文数量 : ウォレット内の資産の50%(通貨ペアの注文に使用できる資産のみ考慮　レバレッジは1倍を想定　ポジションの損益を考慮しない)



def task10minutes(): #10分間に1回実行するための関数として定義します。
    info()

def info():
    

	# - ウォレット残高
    account_info = client.get_account_snapshot(type='SPOT')
    total_asset_of_Btc = account_info['snapshotVos'][0]['data']['totalAssetOfBtc']
    print('ウォレット残高')
    print(f'ウォレット残高(Btc):{total_asset_of_Btc}')
    # どのくらいBNBの残高
    bnb_balance = client.get_asset_balance(asset='BNB')
    print(f'BNB残高:{bnb_balance}')



	# - 損益
    print('損益')
	# - 自分が持つポジションや通貨情報
    [print(x) for x in account_info['snapshotVos'][0]['data']['balances']]


# schedule.every(10).minutes.do(task10minutes) # task10minutesを10分に1回実行します

times = 10

def order():
    symbol='BUSDUSDT'
    side=SIDE_BUY
    type=ORDER_TYPE_LIMIT
    timeInForce=TIME_IN_FORCE_GTC
    quantity = 1
    price='0.0001'

    candles = client.get_klines(symbol=symbol, interval=Client.KLINE_INTERVAL_1MINUTE)

    Open_times = [x[0] for x in candles]
    Opens = [x[1] for x in candles]
    Highs = [x[2] for x in candles]
    Lows = [x[3] for x in candles]
    Closes = [x[4] for x in candles]
    Volumes = [x[5] for x in candles]
    Close_times = [x[6] for x in candles]

    symbol_info = client.get_symbol_info(symbol)
    minprice = symbol_info['filters'][0]['minPrice'] #'0.00010000'
    maxprice = symbol_info['filters'][0]['maxPrice'] #'1000.00000000'
    ticksize = symbol_info['filters'][0]['tickSize'] #'0.00010000'
    minQty = symbol_info['filters'][2]['minQty'] #'1.00000000'
    maxQty = symbol_info['filters'][2]['maxQty'] #'15000000.00000000'
    stepSize = symbol_info['filters'][2]['stepSize'] #'1.00000000'
    [print(x) for x in symbol_info['filters']]


    exitflg = False

    #priceチェック
    if float(maxprice) < float(price):
        print('価格が最大値を超えています {maxprice}以下にしてください')
        exitflg = True
    elif float(price) < float(minprice):
        print(f'価格が最小値を下回っています {minprice}以上にしてください')
        exitflg = True

    if float(maxQty) < float(quantity):
        print(f'購入量が最大値を超えています {maxQty}以下にしてください')
        exitflg = True
    elif float(minQty) > float(quantity):
        print(f'購入量が最小値を下回っています {minQty}以上にしてください')
        exitflg = True

    if exitflg:
        print('order関数を終了します')
        return False
    else:
        print('注文が実行可能です')


    try:
        order = client.create_test_order(
            symbol=symbol,
            side=side,
            type=type,
            timeInForce=timeInForce,
            quantity=quantity,
            price=price)
    except BinanceAPIException as e:
        print(e)
    else:
        print("Test Order Success")



    print(order)

def task10seconds(): #10秒に1回実行される関数として定義します
    global times
    # print(f'このタスクは実行開始から{times}秒後に実行されています')
    times += 10


    # print(order)

def calculate_quantity():
    pass

schedule.every(10).seconds.do(task10seconds) #task10secondsをに1回実行します


def main():
    print(help)
    while True:
        c = sys.stdin.readline()

        print(f'読み込んだ文字{str(c)}')
        if 'quit' in c:
            sys.exit()
        elif 'help' in c:
            print(help)
        elif  'info' in c:
            info()
        elif 'order' in c:
            order()

if __name__ == '__main__':
    main()
    pass

# 制約事項
# APIエンドポイントはBinanceによって1秒あたり20リクエストでレート制限
# 1200リクエスト/分
# 1秒間に10件の注文
# 24時間当たり100,000件の注文

# MLによる制約


# https://sammchardy.github.io/binance-order-filters/