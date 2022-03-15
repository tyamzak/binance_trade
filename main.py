import os
from os.path import join, dirname
from time import sleep
from dotenv import load_dotenv
import schedule
import sys
import threading
from binance.enums import *

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
info : 口座関係情報を出力する(10分に1回、自動的に出力されます)\n'



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
    order = client.pcreate_test_order(
        symbol='BUSDUSDT',
        side=SIDE_BUY,
        type=ORDER_TYPE_LIMIT,
        timeInForce=TIME_IN_FORCE_GTC,
        quantity=100,
        price='0.00001')

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

if __name__ == '__main__':
    main()
    pass

# 制約事項
# APIエンドポイントはBinanceによって1秒あたり20リクエストでレート制限
# 1200リクエスト/分
# 1秒間に10件の注文
# 24時間当たり100,000件の注文