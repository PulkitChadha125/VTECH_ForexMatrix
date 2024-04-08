import time
import traceback
import pandas as pd
from pathlib import Path
import MT5Integration as trade
from datetime import datetime, timedelta, timezone
import pytz
# timezone = pytz.timezone("Etc/UTC")
result_dict = {}
current_date = datetime.today()
last_run_date=current_date - timedelta(days=1)
vantage_timezone ="GMT"
exceness="Etc/UTC"
timezoneused=exceness
# BuyBelow	 NextBuyPts	SellAbove	NextSellPts	CoupleTradeDist	Stoploss	Target	Lotsize


def get_user_settings():
    global result_dict
    try:
        csv_path = 'TradeSettings.csv'
        df = pd.read_csv(csv_path)
        df.columns = df.columns.str.strip()
        result_dict = {}

        for index, row in df.iterrows():
            # Create a nested dictionary for each symbol
            symbol_dict = {
                'BuyBelow': float(row['BuyBelow']),
                'NextBuyPts': float(row['NextBuyPts']),
                'SellAbove': float(row['SellAbove']),
                'MagicNumber': float(row['MagicNumber']),
                'NextSellPts': float(row['NextSellPts']),
                'CoupleTradeDist':float(row['CoupleTradeDist']),
                'Stoploss':float( row['Stoploss']),
                'Target': float(row['Target']),
                'Lotsize': float(row['Lotsize']),
                'InitialTrade':None,
                'CurrTradeBuyLevel':None,
                'CurrTradeSellLevel': None,
                'Orders': []
            }
            result_dict[row['Symbol']] = symbol_dict
        print(result_dict)
    except Exception as e:
        print("Error happened in fetching symbol", str(e))


get_user_settings()

def get_mt5_credentials():
    credentials = {}
    try:
        df = pd.read_csv('MT5Credentials.csv')
        for index, row in df.iterrows():
            title = row['Title']
            value = row['Value']
            credentials[title] = value
    except pd.errors.EmptyDataError:
        print("The CSV file is empty or has no data.")
    except FileNotFoundError:
        print("The CSV file was not found.")
    except Exception as e:
        print("An error occurred while reading the CSV file:", str(e))

    return credentials


credentials_dict = get_mt5_credentials()
Login = credentials_dict.get('Login')
Password = credentials_dict.get('Password')
Server = credentials_dict.get('Server')

print("LoginId:",Login)
print("Server:",Server)
trade.login(Login, Password, Server)


def main_strategy():
    global result_dict
    try:
        for symbol, params in result_dict.items():
            symr = trade.get_data(symbol=symbol, timeframe="TIMEFRAME_M5")
            close = float(symr[0][4])
            timestamp = datetime.now()
            timestamp = timestamp.strftime("%d/%m/%Y %H:%M:%S")
            candletime = symr[0][0]

            if (
                    params['InitialTrade'] == None and
                    close >= params['SellAbove'] and
                    params['SellAbove']>0
            ):
                params['InitialTrade'] ="SHORT"
                params['CurrTradeBuyLevel'] = params['SellAbove']-params['NextBuyPts']
                params['CurrTradeSellLevel'] = params['SellAbove']+params['NextSellPts']
                res= trade.mt_short(symbol=symbol, lot=float(params['Lotsize']), MagicNumber=int(params['MagicNumber']))
                trade_log = {
                            'OrderId': res,
                            'couplebuylevel': params['CurrTradeBuyLevel'],
                            'coupleselllevel': None,
                            'tgt':params['SellAbove']-params['Target'],
                            'sl':params['SellAbove']+params['Stoploss'],
                            'entry_price':params['SellAbove']
                        }
                params['Orders'].append(trade_log)
                # print("Chart Candle time :", candletime)
                Oederog = f"{timestamp} Sell trade executed primary @ {symbol} @ {close}, next buy={params['CurrTradeBuyLevel']}, next sell={params['CurrTradeSellLevel']} "
                print(Oederog)
                write_to_order_logs(Oederog)
                # print("result_dict: ",result_dict)



            if (
                    params['InitialTrade'] == None and
                    close <= params['BuyBelow']and
                    params['BuyBelow'] > 0
            ):
                params['InitialTrade'] ="BUY"
                params['CurrTradeBuyLevel'] = params['BuyBelow'] - params['NextBuyPts']
                params['CurrTradeSellLevel'] = params['BuyBelow'] + params['NextSellPts']
                res=trade.mt_buy(symbol=symbol, lot=float(params['Lotsize']), MagicNumber=int(params['MagicNumber']))

                trade_log = {
                    'OrderId': res,
                    'couplebuylevel': None,
                    'coupleselllevel': params['CurrTradeSellLevel'],
                    'tgt':params['BuyBelow']+params['Target'],
                    'sl':params['BuyBelow']-params['Stoploss'],
                    'entry_price':params['BuyBelow'],
                }

                params['Orders'].append(trade_log)
                # print("Chart Candle time :", candletime)
                Oederog = f"{timestamp} Buy trade executed primary @ {symbol} @ {close}, next buy={params['CurrTradeBuyLevel']}, next sell={params['CurrTradeSellLevel']} "
                print(Oederog)
                write_to_order_logs(Oederog)
                # print("result_dict: ", result_dict)

            if params['InitialTrade'] =="SHORT":
                if close>= params['CurrTradeSellLevel']:
                    ep=params['CurrTradeSellLevel']
                    params['CurrTradeBuyLevel'] = params['CurrTradeSellLevel'] - params['NextBuyPts']
                    params['CurrTradeSellLevel'] = params['CurrTradeSellLevel'] + params['NextSellPts']
                    res = trade.mt_short(symbol=symbol, lot=float(params['Lotsize']),
                                         MagicNumber=int(params['MagicNumber']))

                    trade_log = {
                        'OrderId': res,
                        'couplebuylevel': params['CurrTradeBuyLevel'],
                        'coupleselllevel': None,
                        'tgt':params['CurrTradeSellLevel']-params['Target'],
                            'sl':params['CurrTradeSellLevel']+params['Stoploss'],
                        'entry_price':ep
                    }

                    params['Orders'].append(trade_log)
                    Oederog = f"{timestamp} Sell trade executed secondary @ {symbol} @ {close}, next buy={params['CurrTradeBuyLevel']}, next sell={params['CurrTradeSellLevel']} "
                    print(Oederog)
                    write_to_order_logs(Oederog)
                    # print("result_dict: ", result_dict)

                if close <= params['CurrTradeBuyLevel']:
                    params['CurrTradeSellLevel'] = params['CurrTradeBuyLevel'] + params['NextSellPts']
                    params['CurrTradeBuyLevel'] = params['CurrTradeBuyLevel'] - params['NextBuyPts']
                    Oederog = f"{timestamp} sell secondy loop level updated : CurrTradeBuyLevel: {params['CurrTradeBuyLevel']}, CurrTradeSellLevel:{params['CurrTradeSellLevel']} "
                    print(Oederog)
                    write_to_order_logs(Oederog)
                    # print("result_dict: ", result_dict)


            if params['InitialTrade'] == "BUY":
                if close <= params['CurrTradeBuyLevel']:
                    ep=params['CurrTradeBuyLevel']
                    params['CurrTradeSellLevel'] = params['CurrTradeBuyLevel'] + params['NextSellPts']
                    params['CurrTradeBuyLevel'] = params['CurrTradeBuyLevel'] - params['NextBuyPts']
                    res = trade.mt_buy(symbol=symbol, lot=float(params['Lotsize']), MagicNumber=int(params['MagicNumber']))

                    trade_log = {
                        'OrderId': res,
                        'couplebuylevel': None,
                        'coupleselllevel': params['CurrTradeSellLevel'],
                        'tgt': params['CurrTradeBuyLevel']+params['Target'],
                            'sl': params['CurrTradeBuyLevel']-params['Stoploss'],
                        'entry_price': ep,
                    }

                    params['Orders'].append(trade_log)
                    # print("Chart Candle time :", candletime)

                    Oederog = f"{timestamp} Buy trade executed secondary @ {symbol} @ {close}, next buy={params['CurrTradeBuyLevel']}, next sell={params['CurrTradeSellLevel']} "
                    print(Oederog)
                    write_to_order_logs(Oederog)
                    print("result_dict: ", result_dict)

                if close >= params['CurrTradeSellLevel']:
                    params['CurrTradeBuyLevel'] = params['CurrTradeSellLevel'] - params['NextBuyPts']
                    params['CurrTradeSellLevel'] = params['CurrTradeSellLevel'] + params['NextSellPts']

                    Oederog = f"{timestamp} buy secondy loop level updated : CurrTradeBuyLevel: {params['CurrTradeBuyLevel']}, CurrTradeSellLevel:{params['CurrTradeSellLevel']} "
                    print(Oederog)
                    write_to_order_logs(Oederog)

            for order in params['Orders']:
                order_id = order['OrderId']
                couple_buy_level = order['couplebuylevel']
                couple_sell_level = order['coupleselllevel']
                entry_price = float(order['entry_price'])



                if params['InitialTrade'] =="SHORT":
                    if close<=couple_buy_level and couple_buy_level>0:
                        res=trade.changeslpl(
                            ticket=order_id,
                            pair=symbol,
                            pos_type="SHORT",
                            SL=float(params["Stoploss"]),
                            tp=float(params["Target"]),
                            ea_magic_number=int(params['MagicNumber']),
                            volume=float(params['Lotsize']),
                            reference_price=float(entry_price)
                        )
                        print("OrderModify: ",res)
                        Oederog = f"{timestamp} Couple Buy trade executed @ {symbol} @ {close} target sl modified for sell order id {order_id} "
                        print(Oederog)
                        write_to_order_logs(Oederog)
                        params['Orders'].remove(order)
                        trade.mt_buy_bracket(
                            symbol=symbol,
                            lot=float(params['Lotsize']),
                            MagicNumber=int(params['MagicNumber']),
                            sl=float(params["Stoploss"]),
                            tp=float(params["Target"]),
                            reference_price=float(couple_buy_level)
                        )
                        couple_buy_level = 0
                        order['couplebuylevel'] = 0


                if params['InitialTrade'] == "BUY":
                    if close >= couple_sell_level and couple_sell_level>0:
                        trade.changeslpl(
                            ticket=order_id,
                            pair=symbol,
                            pos_type="BUY",
                            SL=float(params["Stoploss"]),
                            tp=float(params["Target"]),
                            ea_magic_number=int(params['MagicNumber']),
                            volume=float(params['Lotsize']),
                            reference_price=float(entry_price)
                        )
                        Oederog = f"{timestamp} Couple Sell trade executed @ {symbol} @ {close} target sl modified for Buy order id {order_id} "
                        print(Oederog)
                        write_to_order_logs(Oederog)
                        params['Orders'].remove(order)
                        trade.mt_sell_bracket(
                            symbol=symbol,
                            lot=float(params['Lotsize']),
                            MagicNumber=int(params['MagicNumber']),
                            sl=float(params["Stoploss"]),
                            tp=float(params["Target"]),
                            reference_price=float(couple_sell_level)
                        )
                        couple_sell_level = 0
                        order['coupleselllevel'] = 0


    except Exception as e:
        print("Error happened in Main strategy loop: ", str(e))
        traceback.print_exc()

def write_to_order_logs(message):
    with open('OrderLogs.txt', 'a') as file:  # Open the file in append mode
        file.write(message + '\n')



end_date = datetime(2024, 4, 13)
while True:
    main_strategy()


