import os
from os.path import join, dirname
from time import sleep
from turtle import fd
from dotenv import load_dotenv
import schedule
import sys
import threading
from binance.enums import *
from binance.exceptions import BinanceAPIException
import datetime
import numpy as np
from fractions import Fraction
import decimal

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


    order_symbol='TUSDBUSD'

    order_side=SIDE_BUY
    order_type=ORDER_TYPE_TAKE_PROFIT_LIMIT
    order_timeInForce=TIME_IN_FORCE_GTC
    order_quantity = '10.00000000'  #後に上書きされる
    order_price='1.00000'           #後に上書きされる
    order_stopprice = '1.00000'     #後に上書きされる

    revorder_side=SIDE_SELL
    revorder_type=ORDER_TYPE_TAKE_PROFIT_LIMIT
    revorder_timeInForce=TIME_IN_FORCE_GTC
    revorder_quantity = '10.00000000'  #後に上書きされる
    revorder_price='1.00000'           #後に上書きされる
    revorder_stopprice = '1.00000'     #後に上書きされる

    chk_order = client.get_open_orders(symbol=order_symbol)

    # orderが1つ以上ある場合は取引を実施しない
    if len(chk_order) > 0:
        print(('オープンなオーダーが存在するため、中止します'))
        return False


    #1分間のローソク足を取得する
    candles = client.get_klines(symbol=order_symbol, interval=Client.KLINE_INTERVAL_1MINUTE)

    Open_times = [x[0] for x in candles] #datetime.fromtimestampの際は、上から10桁を使用のこと
    Opens = [x[1] for x in candles]
    Highs = [x[2] for x in candles]
    Lows = [x[3] for x in candles]
    Closes = [x[4] for x in candles]
    Volumes = [x[5] for x in candles]
    Close_times = [x[6] for x in candles]

    #取引手数料を取得する
    fees = client.get_trade_fee(symbol=order_symbol)
    makercommission = fees[0]['makerCommission']
    takercommission = fees[0]['takerCommission']
    print(f'取引手数料 maker commission : {makercommission}')
    print(f'取引手数料 taker commission : {takercommission}')

    symbol_info = client.get_symbol_info(order_symbol)
    minprice = symbol_info['filters'][0]['minPrice'] 
    maxprice = symbol_info['filters'][0]['maxPrice'] 
    ticksize = symbol_info['filters'][0]['tickSize'] 
    minQty = symbol_info['filters'][2]['minQty'] 
    maxQty = symbol_info['filters'][2]['maxQty'] 
    stepSize = symbol_info['filters'][2]['stepSize'] 
    multiplierUp = symbol_info['filters'][1]['multiplierUp'] 
    multiplierDown = symbol_info['filters'][1]['multiplierDown'] 
    baseAssetPrecision = symbol_info['baseAssetPrecision']
    quoteAssetPrecision = symbol_info['quoteAssetPrecision']

    #5分間の平均価格
    avg5min = np.average([float(x) for x in Closes[-5:]])

    #5分間の平均価格 x multiplierUp
    maxprice_percentfilter = float(avg5min) * float(multiplierUp)

    #5分間の平均価格 x multiplierDown
    minprice_percentfilter = float(avg5min) * float(multiplierDown)

    #過去10分の最安値を取得
    min_10min = np.min([float(x) for x in Lows[-10:]])
    print(f'過去10分の最安値: {min_10min}')

    #過去10分の最高値を取得
    max_10min = np.max([float(x) for x in Highs[-10:]])
    print(f'過去10分の最高値: {max_10min}')

    min_notional = symbol_info['filters'][3]['minNotional']


    #order_priceを更新　過去10分の最高値にする
    order_price = min_10min
    order_stopprice = min_10min

    #order_stoppriceを更新 過去10分の最安値にする
    revorder_price = max_10min
    revorder_stopprice = max_10min


    #BUY側の処理
    #現在保有しているQuote通貨の半分を取得する
    half_quote_asset = float(client.get_asset_balance(asset=symbol_info['quoteAsset'])['free']) / 2

    #通過の半分に相当するorder quantityを計算する
    half_quantity = decimal.Decimal(str(half_quote_asset)) // decimal.Decimal(str(stepSize)) * decimal.Decimal(str(stepSize))

    #小数点以下Precision桁の文字列型にする
    order_quantity = '{:.{}f}'.format(half_quantity, quoteAssetPrecision)

    #SELL側の処理
    #現在保有しているBase通貨の半分を取得する
    half_base_asset = float(client.get_asset_balance(asset=symbol_info['baseAsset'])['free']) / 2
    #通過の半分に相当するorder quantityを計算する
    revhalf_quantity = decimal.Decimal(str(half_base_asset)) // decimal.Decimal(str(stepSize)) * decimal.Decimal(str(stepSize))
    #小数点以下Precision桁の文字列型にする
    revorder_quantity = '{:.{}f}'.format(revhalf_quantity, baseAssetPrecision)

    # #テスト用の値入力
    # order_price = '0.90000'
    # order_stopprice = order_price
    # order_quantity = '12.00000000'

    # revorder_price = '1.20000'
    # revorder_stopprice = revorder_price
    # revorder_quantity = '12.00000000'


    # [print(x) for x in symbol_info['filters']]


    exitflg = False
    revexitflg = False

    #BUY側チェック

    #価格Filterのチェック
    if float(maxprice) < float(order_price):
        print(f'価格が最大値を超えています {maxprice}以下にしてください')
        exitflg = True
    elif float(order_price) < float(minprice):
        print(f'価格が最小値を下回っています {minprice}以上にしてください')
        exitflg = True

    #購入量Filterのチェック
    if float(maxQty) < float(order_quantity):
        print(f'購入量が最大値を超えています {maxQty}以下にしてください')
        exitflg = True
    elif float(minQty) > float(order_quantity):
        print(f'購入量が最小値を下回っています {minQty}以上にしてください')
        exitflg = True

    #PercentPriceのチェック
    if float(maxprice_percentfilter) < float(order_price):
        print(f'価格が最大値を超えています {maxprice_percentfilter}以下にしてください')
        exitflg = True
    elif float(order_price) < float(minprice_percentfilter):
        print(f'価格が最小値を下回っています {minprice_percentfilter}以上にしてください')
        exitflg = True

    #MIN_NOTIONALのチェック
    if float(min_notional) >= float(order_price) * float(order_quantity):
        print(f'"price x quantityの値がMIN_NOTIONALを下回っています。\n{min_notional}以上にしてください')
        exitflg = True

    #SELL側チェック
    #価格Filterのチェック
    if float(maxprice) < float(revorder_price):
        print(f'価格が最大値を超えています {maxprice}以下にしてください')
        revexitflg = True
    elif float(revorder_price) < float(minprice):
        print(f'価格が最小値を下回っています {minprice}以上にしてください')
        revexitflg = True

    #購入量Filterのチェック
    if float(maxQty) < float(revorder_quantity):
        print(f'購入量が最大値を超えています {maxQty}以下にしてください')
        revexitflg = True
    elif float(minQty) > float(revorder_quantity):
        print(f'購入量が最小値を下回っています {minQty}以上にしてください')
        revexitflg = True

    #PercentPriceのチェック
    if float(maxprice_percentfilter) < float(revorder_price):
        print(f'価格が最大値を超えています {maxprice_percentfilter}以下にしてください')
        revexitflg = True
    elif float(revorder_price) < float(minprice_percentfilter):
        print(f'価格が最小値を下回っています {minprice_percentfilter}以上にしてください')
        revexitflg = True

    #MIN_NOTIONALのチェック
    if float(min_notional) >= float(revorder_price) * float(revorder_quantity):
        print(f'"price x quantityの値がMIN_NOTIONALを下回っています。\n{min_notional}以上にしてください')
        revexitflg = True


    if exitflg:
        print('BUY注文を終了します')

    else:
        print('BUY注文が実行可能と判定しました')

        try:
            order = client.create_test_order(
                symbol=order_symbol,
                side=order_side,
                type=order_type,
                timeInForce=order_timeInForce,
                quantity=order_quantity,
                price=order_price,
                stopPrice=order_stopprice)
            
        except BinanceAPIException as e:
            print(e)
            if e.code == -1021:
                print("サーバーの時間の更新が必要かもしれません")
            elif e.code == -1013:
                print("price x quantityの値がMIN_NOTIONALを下回っています。\n1回の取引量の増量が必要です")

            return False

        else:
            print("Test Order Success")
            print("以下の内容で注文を実行します")
            print(f"symbol : {order_symbol}")
            print(f"side : {order_side}")
            print(f"type : {order_type}")
            print(f"timeInForce : {order_timeInForce}")
            print(f"quantity : {order_quantity}")
            print(f"price : {order_price}")
            print(f"stopPrice : {order_stopprice}")

            try:
                
                order = client.create_order(
                    symbol=order_symbol,
                    side=order_side,
                    type=order_type,
                    timeInForce=order_timeInForce,
                    quantity=order_quantity,
                    price=order_price,
                    stopPrice=order_stopprice)
            
            except BinanceAPIException as e:
                print(e)
            else:
                print('買い注文完了')
                print(client.get_open_orders(symbol=order_symbol))
                info()

    if revexitflg:
        print('SELL注文を終了します')
    else:
        print('SELL注文が実行可能と判定しました')

        try:
            order = client.create_test_order(
                symbol=order_symbol,
                side=revorder_side,
                type=revorder_type,
                timeInForce=revorder_timeInForce,
                quantity=revorder_quantity,
                price=revorder_price,
                stopPrice=revorder_stopprice)
            
        except BinanceAPIException as e:
            print(e)
            if e.code == -1021:
                print("サーバーの時間の更新が必要かもしれません")
            elif e.code == -1013:
                print("price x quantityの値がMIN_NOTIONALを下回っています。\n1回の取引量の増量が必要です")



        else:
            print("Test Order Success")
            print("以下の内容で注文を実行します")
            print(f"symbol : {order_symbol}")
            print(f"side : {revorder_side}")
            print(f"type : {revorder_type}")
            print(f"timeInForce : {revorder_timeInForce}")
            print(f"quantity : {revorder_quantity}")
            print(f"price : {revorder_price}")
            print(f"stopPrice : {revorder_stopprice}")


            try:
                
                order = client.create_order(
                    symbol=order_symbol,
                    side=revorder_side,
                    type=revorder_type,
                    timeInForce=revorder_timeInForce,
                    quantity=revorder_quantity,
                    price=revorder_price,
                    stopPrice=revorder_stopprice)
                
            except BinanceAPIException as e:
                print(e)
            else:
                print('売り注文完了')
                print(client.get_open_orders(symbol=order_symbol))
                info()



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