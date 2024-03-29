# -*- coding: utf-8 -*-

import asyncio
import MetaTrader5 as mt5
import pandas as pd
import os
import pathlib
import pytz
import time
from datetime import datetime
import pandas_ta as ta
from LineNotify import LineNotify

import config

import stupid_share
import stupid_volty_mt5

import logging
from logging.handlers import RotatingFileHandler

import json
class TPLS(object):
    def __init__(self):
        self.is_buy_tp_percent=True
        self.buy_tp=0.0
        self.is_buy_sl_percent=True
        self.buy_sl=0.0

        self.is_sell_tp_percent=True
        self.sell_tp=0.0
        self.is_sell_sl_percent=True
        self.sell_sl=0.0

        self.tp_amount=0.0

bot_name = 'Volty'
bot_prefix = 'VT'
bot_vesion = '1.4.9'

bot_fullname = f'MT5 {bot_name} version {bot_vesion}'

# ansi escape code
CLS_SCREEN = '\033[2J\033[1;1H' # cls + set top left
CLS_LINE = '\033[0J'
SHOW_CURSOR = '\033[?25h'
HIDE_CURSOR = '\033[?25l'
CRED  = '\33[31m'
CGREEN  = '\33[32m'
CYELLOW  = '\33[33m'
CMAGENTA  = '\33[35m'
CCYAN  = '\33[36m'
CEND = '\033[0m'
CBOLD = '\33[1m'

notify = LineNotify(config.LINE_NOTIFY_TOKEN)

symbol = config.symbols[0]
tf = config.timeframe[0]
lot = config.lot
deviation = config.deviation

magic_number = config.magic_number

user_id = config.LOGIN
server_user = config.SERVER
password_user = config.PASSWORD
mt5_path = config.PATH

TZ_ADJUST = 7
MT_ADJUST = 4

TIMEFRAME_SECONDS = {
    '1m': 60,
    '3m': 60*3,
    '5m': 60*5,
    '15m': 60*15,
    '30m': 60*30,
    '1h': 60*60,
    '2h': 60*60*2,
    '4h': 60*60*4,
    '6h': 60*60*6,
    '8h': 60*60*8,
    '12h': 60*60*12,
    '1d': 60*60*24,
}
UB_TIMER_SECONDS = [
    TIMEFRAME_SECONDS[tf],
    10,
    15,
    20,
    30,
    60,
    int(TIMEFRAME_SECONDS[tf]/2)
]

SHOW_COLUMNS = ['symbol', 'identifier', 'type', 'volume', 'price_open', 'sl', 'tp', 'price_current', 'profit', 'comment', 'magic']
RENAME_COLUMNS = ['Symbol', 'Ticket', 'Type', 'Volume', 'Price', 'S/L', 'T/P', 'Last', 'Profit', 'Comment', 'Magic']

ORDER_TYPE = ["buy","sell","buy limit","sell limit","buy stop","sell stop","buy stop limit","sell stop limit","close"]

all_stat = {}

symbols_list = []
symbols_tf = {}
symbols_next_tf_ticker = {}
symbols_trade = {}

symbols_tpsl = {}

all_signals = {}

trade_count = {}
buy_count = {}
sell_count = {}
rw_count = {}

min_dd = 0.0

init_balance = 0.0

report_json_path = './datas/orders_report.json'

def broker_symbol(symbol):
    if len(config.symbol_suffix) > 0:
        if config.symbol_suffix in symbol:
            return symbol
        else:
            return symbol + config.symbol_suffix
    else:
        return symbol
def symbol_only(symbol):
    if len(config.symbol_suffix) > 0:
        return symbol.replace(config.symbol_suffix, '')
    else:
        return symbol
    
def trade_buy(base_symbol, price, lot=lot, tp=0.0, sl=0.0, magic_number=magic_number, step=0, tag=""):
    symbol = broker_symbol(base_symbol)
    point = mt5.symbol_info(symbol).point
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": mt5.ORDER_TYPE_BUY,
        "price": price,
        "deviation": deviation,
        "magic": magic_number,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    if sl > 0:
        request["sl"] = sl
    if 'sl' in request.keys():
        sl_pips = int(abs(price - request['sl']) / point + 0.5)
        request["comment"] = f"{bot_prefix}{tag}-{sl_pips}-{step}"
    else:
        request["comment"] = f"{bot_prefix}{tag}-{step}"
    if tp > 0:
        request["tp"] = tp
    logger.info(f"{base_symbol} trade_buy :: request = {request}")
    # send a trading request
    result = mt5.order_send(request)
    position_id_buy = 0
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        logger.info(f"{base_symbol} trade_buy :: order_send failed, retcode = {result.retcode}")
        logger.debug(f"{base_symbol} trade_buy :: result = {result}")
    else:
        logger.info(f"{base_symbol} trade_buy :: order = {result.order}")
        t_req = result.request
        logger.debug(f"{base_symbol} trade_buy :: result.request = {t_req}")
        tp_txt = ""
        sl_txt = ""
        if t_req.tp > 0:
            tp_txt = f"\nTP = {t_req.tp}"
        if t_req.sl > 0:
            sl_txt = f"\nSL = {t_req.sl}"
        notify.Send_Text(f"{base_symbol}\nTrade Buy {step} {tag}\nPrice = {t_req.price}\nLot = {t_req.volume}{tp_txt}{sl_txt}", True)
        position_id_buy = result.order
    return position_id_buy

def close_buy(base_symbol, position_id, lot, price_open):
    symbol = broker_symbol(base_symbol)
    price = mt5.symbol_info_tick(symbol).bid
    profit = 0.0
    if price_open > 0.0:
        profit = (price - price_open)
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": mt5.ORDER_TYPE_SELL,
        "position": position_id,
        "price": price,
        "deviation": deviation,
        # "magic": magic_number,
        "comment": bot_prefix,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    # if magic_number > 0:
    #     request["magic"] = magic_number
    # send a trading request
    result = mt5.order_send(request)
    position_id_close_buy = 0
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        logger.info(f"{base_symbol} close_buy :: order_send failed, retcode = {result.retcode}")
        logger.debug(f"{base_symbol} close_buy :: result = {result}")
    else:
        logger.info(f"{base_symbol} close_buy :: order = {result.order}")
        t_req = result.request
        logger.debug(f"{base_symbol} close_buy :: result.request = {t_req}")
        notify.Send_Text(f"{base_symbol}\nTrade Close Buy\n#{position_id}\nPrice = {t_req.price}\nProfit = {profit:.2f}", True)
        position_id_close_buy = result.order
    return position_id_close_buy

def trade_sell(base_symbol, price, lot=lot, tp=0.0, sl=0.0, magic_number=magic_number, step=0, tag=""):
    symbol = broker_symbol(base_symbol)
    point = mt5.symbol_info(symbol).point 
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": mt5.ORDER_TYPE_SELL,
        "price": price,
        "deviation": deviation,
        "magic": magic_number,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    if sl > 0:
        request["sl"] = sl
    if 'sl' in request.keys():
        sl_pips = int(abs(price - request['sl']) / point + 0.5)
        request["comment"] = f"{bot_prefix}{tag}-{sl_pips}-{step}"
    else:
        request["comment"] = f"{bot_prefix}{tag}-{step}"
    if tp > 0:
        request["tp"] = tp
    logger.info(f"{base_symbol} trade_sell :: request = {request}")
    # send a trading request
    result = mt5.order_send(request)
    position_id_sell = 0
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        logger.info(f"{base_symbol} trade_sell :: order_send failed, retcode = {result.retcode}")
        logger.debug(f"{base_symbol} trade_sell :: result = {result}")
    else:
        logger.info(f"{base_symbol} trade_sell :: order = {result.order}")
        t_req = result.request
        logger.debug(f"{base_symbol} trade_sell :: result.request = {t_req}")
        tp_txt = ""
        sl_txt = ""
        if t_req.tp > 0:
            tp_txt = f"\nTP = {t_req.tp}"
        if t_req.sl > 0:
            sl_txt = f"\nSL = {t_req.sl}"
        notify.Send_Text(f"{base_symbol}\nTrade Sell {step} {tag}\nPrice = {t_req.price}\nLot = {t_req.volume}{tp_txt}{sl_txt}", True)
        position_id_sell = result.order
    return position_id_sell  

def close_sell(base_symbol, position_id, lot, price_open):
    symbol = broker_symbol(base_symbol)
    price = mt5.symbol_info_tick(symbol).ask
    profit = 0.0
    if price_open > 0.0:
        profit = (price_open - price)
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": mt5.ORDER_TYPE_BUY,
        "position": position_id,
        "price": price,
        "deviation": deviation,
        # "magic": magic_number,
        "comment": bot_prefix,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    # if magic_number > 0:
    #     request["magic"] = magic_number
    # send a trading request
    result = mt5.order_send(request)
    position_id_close_sell = 0
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        logger.info(f"{base_symbol} close_sell :: order_send failed, retcode = {result.retcode}")
        logger.debug(f"{base_symbol} close_sell :: result = {result}")
    else:
        logger.info(f"{base_symbol} close_sell :: order = {result.order}")
        t_req = result.request
        logger.debug(f"{base_symbol} close_sell :: result.request = {t_req}")
        notify.Send_Text(f"{base_symbol}\nTrade Close Sell\n#{position_id}\nPrice = {t_req.price}\nProfit = {profit:0.2f}", True)
        position_id_close_sell = result.order
    return position_id_close_sell

def close_position(position):
    if position["type"] == ORDER_TYPE[1]:
        position_id = close_sell(position['symbol'], position['identifier'], position['volume'], position['price_open'])
    elif position["type"] == ORDER_TYPE[0]:
        position_id = close_buy(position['symbol'], position['identifier'], position['volume'], position['price_open'])

def close_by_profit(symbols_list):
    # logger.info(f"close by profit ...")
    for base_symbol in symbols_list:
        symbol_positions = positions_get(base_symbol)
        if len(symbol_positions) == 0:
            logger.info(f"close_by_profit:: no positions")
            return
        # target_positions = symbol_positions.loc[(symbol_positions["comment"].str.startswith(f'{bot_prefix}-', na=False)) & (symbol_positions["magic"] == magic_number)]
        target_positions = symbol_positions.loc[(symbol_positions["comment"].str.startswith(f'{bot_prefix}-', na=False))]
        all_profit = sum(target_positions['profit'])
        logger.info(f"{base_symbol} close_by_profit :: all profit = {all_profit:.2f} :: tp_amount = {symbols_tpsl[base_symbol].tp_amount}")
        if symbols_tpsl[base_symbol].tp_amount > 0 and all_profit >= symbols_tpsl[base_symbol].tp_amount:
            for index, position in target_positions.iterrows():
                close_position(position)
            notify.Send_Text(f"Total Profit: {all_profit}")

# Function to modify an open position
def modify_position(base_symbol, position_id, new_sl, new_tp, magic_number=magic_number, step=0, tag=""):
    symbol = broker_symbol(base_symbol)
    logger.debug(f"{symbol} modify_position :: position_id = {position_id} : SL {new_sl} : TP {new_tp} : magic_number = {magic_number}")
    # Create the request
    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "symbol": symbol,
        # "sl": new_sl,
        # "tp": new_tp,
        "position": position_id,
        # "magic": magic_number,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    if new_sl > 0:
        request["sl"] = new_sl
    if new_tp > 0:
        request["tp"] = new_tp
    # if magic_number != config.magic_number:
    #     request["magic"] = magic_number
    #     request["comment"] = f"{bot_prefix}{tag}#{magic_number}-{step}"
    # Send order to MT5
    result = mt5.order_send(request)
    # logger.debug(f"{symbol} modify_position :: retcode = {result.retcode}")
    logger.debug(f"{symbol} modify_position :: result = {result}")
    if result[0] == 10009:
        logger.info(f"{symbol} modify_position :: order = {result.order}")
        return True
    else:
        return False
# Function to update trailing stop if needed
def update_trailing_stop(position):
    # not revise code, don't use it now
    symbol = position['symbol']
    symbol_info = mt5.symbol_info(symbol)
    symbol_digits = symbol_info.digits
    pip_size = symbol_info.point
    comment_info = position["comment"].split("-")
    if len(comment_info) != 3:
        # logger.debug(f"{symbol} skip update_trailing_stop :: comment_info = {comment_info}")
        return
    step = int(comment_info[-1])
    trailing_stop_pips = int(comment_info[-2])

    # cal tp sl
    position_tp = position['tp']
    position_sl = position['sl']
    if position_tp == 0.0:
        fibo_data = cal_tpsl(symbol, stupid_share.Direction.LONG if position['type'] == ORDER_TYPE[0] else stupid_share.Direction.SHORT, position['price_open'])
        position_tp = fibo_data['tp']
        position_sl = fibo_data['sl']
        # Create updated values for order
        position_id = position['ticket']
        modify_position(symbol, position_id, round(position_sl, symbol_digits), round(position_tp, symbol_digits))
    else:
        # Convert trailing_stop_pips into pips
        trailing_stop_price = trailing_stop_pips * pip_size
        # Determine if Red or Green
        # A Green Position will have a take_profit > stop_loss
        if position['type'] == ORDER_TYPE[0]:
            # If Green, new_stop_loss = current_price - trailing_stop_price
            new_stop_loss = position['price_current'] - trailing_stop_price
            # Test to see if new_stop_loss > current_stop_loss
            if new_stop_loss > position_sl:
                # Create updated values for order
                position_id = position['ticket']
                # New take_profit will be the difference between new_stop_loss and old_stop_loss added to take profit
                # new_take_profit = position['tp'] + new_stop_loss - position['sl']
                logger.debug(f"{symbol} buy :: pip_size={pip_size:.8f} trailing_stop_pips={trailing_stop_pips}")
                # logger.debug(f"{symbol} buy :: {position['sl']:.8f}/{position['tp']:.8f} new sl/tp={new_stop_loss:.8f}/{new_take_profit:.8f}")
                logger.debug(f"{symbol} buy :: {position_sl:.8f}/{position_tp:.8f} new sl={new_stop_loss:.8f}")
                # Send order to modify_position
                modify_position(symbol, position_id, round(new_stop_loss, symbol_digits) , round(position_tp, symbol_digits))
        # A Red Position will have a take_profit < stop_loss
        elif position['type'] == ORDER_TYPE[1]:
            # If Red, new_stop_loss = current_price + trailing_stop_price
            new_stop_loss = position['price_current'] + trailing_stop_price
            # Test to see if new_stop_loss < current_stop_loss
            if new_stop_loss < position_sl:
                # Create updated values for order
                position_id = position['ticket']
                # New take_profit will be the difference between new_stop_loss and old_stop_loss subtracted from old take_profit
                # new_take_profit = position['tp'] - new_stop_loss + position['sl']
                logger.debug(f"{symbol} sell :: pip_size={pip_size:.8f} trailing_stop_pips={trailing_stop_pips}")
                # logger.debug(f"{symbol} sell :: {position['sl']:.8f}/{position['tp']:.8f} new sl/tp={new_stop_loss:.8f}/{new_take_profit:.8f}")
                logger.debug(f"{symbol} sell :: {position_sl:.8f}/{position_tp:.8f} new sl={new_stop_loss:.8f}")
                # Send order to modify_position
                modify_position(symbol, position_id, round(new_stop_loss, symbol_digits), round(position_tp, symbol_digits))

def show_bid_ask(base_symbol):
    symbol = broker_symbol(base_symbol)
    symbol_tick = mt5.symbol_info_tick(symbol)
    ask_price = symbol_tick.ask
    bid_price = symbol_tick.bid
    print(f"\r[{symbol}] Ask Price: {ask_price}, Bid Price: {bid_price}")

def positions_check(positions, old_position_ids, account_info_dict):
    if len(positions) == 0:
        return
    current_position_ids = positions["ticket"].tolist()
    position_ids = [id for id in old_position_ids if id not in current_position_ids]
    for position_id in position_ids:
        position_history_orders = mt5.history_orders_get(position=position_id)
        if position_history_orders != None and len(position_history_orders) >= 2:
            logger.debug(f"position_id = {position_id}")
            df = pd.DataFrame(list(position_history_orders),columns=position_history_orders[0]._asdict().keys())
            # df.drop(['time_setup','time_setup_msc','time_expiration','type_time','state','position_by_id','reason','volume_current','price_stoplimit','sl','tp'], axis=1, inplace=True)
            # df['time_setup'] = pd.to_datetime(df['time_setup'], unit='s')
            # df['time_done'] = pd.to_datetime(df['time_done'], unit='s')
            # logger.debug(f"\n{df.columns}")
            symbol = df['symbol'].iloc[0]
            base_symbol = symbol_only(symbol)
            point = mt5.symbol_info(symbol).point
            logger.debug(f"positions_check {base_symbol}\n{df[['position_id', 'type', 'type_filling', 'volume_initial', 'price_open', 'price_current', 'comment']]}")
            close_by = ''
            order_type = ''
            price_current = 0.0
            profit = 0.0
            volumn = 0.0
            for idx, row in df.iterrows():
                profit += (-1 if row['type'] == 0 else 1) * row['price_current'] * row['volume_initial'] / point
                if 'tp' in row['comment']:
                    close_by = 'TP'
                    # price_current = row['price_current']
                    volumn = row['volume_initial']
                elif 'sl' in row['comment']:
                    close_by = 'SL'
                    # price_current = row['price_current']
                    volumn = row['volume_initial']
                elif row['comment'].startswith(bot_prefix):
                    order_type = 'Buy' if row['type'] == 0 else 'Sell'
                    close_by = bot_prefix
                    # price_current = row['price_current']
                    volumn = row['volume_initial']
                else:
                    logger.debug(f"{base_symbol} close_by :: comment = {row['comment']}")
                # logger.debug(f"profit = {profit}")
            all_stat[base_symbol]["lot"] += round(volumn, 2)
            all_stat[base_symbol]["summary_profit"] += round(profit , 2)
            if profit > 0:
                all_stat[base_symbol]["win"] += 1
                all_stat[base_symbol]["last_loss"] = 0
            elif profit < 0:
                all_stat[base_symbol]["loss"] += 1
                all_stat[base_symbol]["last_loss"] += 1
            if close_by != '':
                notify.Send_Text(f"{base_symbol}\n{close_by} Close {order_type}\n#{position_id}\nProfit = {profit:.2f}", True)
                notify.Send_Text(f"\nBalance = {account_info_dict['balance']}\nEquity = {account_info_dict['equity']}", True)
                notify.Send_Text(f'\nWin:Loss = {all_stat[base_symbol]["win"]}:{all_stat[base_symbol]["loss"]}\nPNL = {all_stat[base_symbol]["summary_profit"]:0.2f}', True)
                if config.rebate_rate_usd > 0:
                    notify.Send_Text(f'Total Lot = {all_stat[base_symbol]["lot"]:0.2f}\nRebate = {config.rebate_rate_usd*all_stat[base_symbol]["lot"]:0.4f}')
                else:
                    notify.Send_Text(f'Total Lot = {all_stat[base_symbol]["lot"]:0.2f}')
                logger.debug(f"{base_symbol} all_stat: {all_stat[base_symbol]}")

                all_stat["init_balance"] = init_balance
                all_stat["min_dd"] = min_dd
                save_to_json(report_json_path, all_stat)

def positions_report(positions):
    global min_dd
    if len(positions) > 0:
        positions.sort_values(by=['profit'], ignore_index=True, ascending=False, inplace=True)
        positions.index = positions.index + 1
        display_positions = positions[SHOW_COLUMNS]
        display_positions.columns = RENAME_COLUMNS
        print(display_positions)
        sum_profit = sum(display_positions['Profit'])
        min_dd = min(sum_profit, min_dd)
        print(f"Total Profit   : {sum_profit:,.2f}")
        print(f"Minimun Profit : {min_dd:,.2f}")
    else:
        print("No Positions")
    summary_columns = ["Symbol", "TF", "Win", "Loss", "Gale", "Lot", "Profit"]
    summary_rows = []
    for base_symbol in symbols_list:
        if base_symbol in all_stat.keys():
            summary_rows.append([base_symbol,symbols_tf[base_symbol],all_stat[base_symbol]["win"],all_stat[base_symbol]["loss"],all_stat[base_symbol]["last_loss"],'{:0.2f}'.format(all_stat[base_symbol]["lot"]),'{:0.2f}'.format(all_stat[base_symbol]["summary_profit"])])
    summary_df = pd.DataFrame(summary_rows,columns=summary_columns)
    summary_df.sort_values(by=['Profit'], ignore_index=True, ascending=False, inplace=True)
    summary_df.index = summary_df.index + 1
    print(summary_df)
    
def positions_getall(symbols_list):
    res = mt5.positions_get()
    if(res is not None and res != ()):
        all_columns = res[0]._asdict().keys()
        df = pd.DataFrame(list(res),columns=all_columns)
        # df["time"] = pd.to_datetime(df["time"], unit="s")
        df["time"] = pd.to_datetime(df["time"], unit="s").map(
            lambda x: x+pd.Timedelta(hours=MT_ADJUST)
        )
        df["symbol"] = df["symbol"].map(lambda x: symbol_only(x)) 
        df["type"] = df["type"].map(lambda x: ORDER_TYPE[x])
        df.drop(df[df["symbol"].isin(symbols_list) == False].index, inplace=True)
        # logger.debug(df.columns)
        return df
    
    return pd.DataFrame()
def positions_get(base_symbol):
    symbol = broker_symbol(base_symbol)
    res = mt5.positions_get(symbol=symbol)
    if(res is not None and res != ()):
        all_columns = res[0]._asdict().keys()
        df = pd.DataFrame(list(res),columns=all_columns)
        # df["time"] = pd.to_datetime(df["time"], unit="s")
        df["time"] = pd.to_datetime(df["time"], unit="s").map(
            lambda x: x+pd.Timedelta(hours=MT_ADJUST)
        )
        df["symbol"] = df["symbol"].map(lambda x: symbol_only(x)) 
        df["type"] = df["type"].map(lambda x: ORDER_TYPE[x])
        # logger.debug(df.columns)
        return df
    
    return pd.DataFrame()

def cal_martingal_lot(symbol, is_double_lot=False):
    cal_lot = config.lot
    if config.is_martingale and config.martingale_max > 0:
        if all_stat[symbol]["last_loss"] < config.martingale_max:
            if config.martingale_factor == 1:
                cal_lot = round(config.lot * (all_stat[symbol]["last_loss"]+1), 2)
            else:
                cal_lot = round(config.lot * (config.martingale_factor ** all_stat[symbol]["last_loss"]), 2)
        else:
            if config.martingale_factor == 1:
                cal_lot = round(config.lot * config.martingale_max, 2)
            else:
                cal_lot = round(config.lot * (config.martingale_factor ** config.martingale_max), 2)
    if is_double_lot:
        cal_lot = round(cal_lot * 2.0, 2)

    return cal_lot

def cal_tpsl(base_symbol, direction:stupid_share.Direction, price_target):
    symbol = broker_symbol(base_symbol)
    symbol_info = mt5.symbol_info(symbol)
    symbol_digits = symbol_info.digits
    symbol_point = symbol_info.point
    tp = 0.0
    sl = 0.0
    if config.is_auto_tpsl:
        fibo_data = stupid_share.cal_minmax_fibo(base_symbol, stupid_volty_mt5.all_candles[base_symbol], direction, entryPrice=price_target, digits=symbol_digits)
        tp = fibo_data['tp']
        sl = fibo_data['sl']
    else:
        fibo_data = {
            'position' : 'BUY' if direction == stupid_share.Direction.LONG else 'SELL',
            'price': round(price_target, symbol_digits),
            'price_txt': 'Price: @{}'.format(round(price_target, symbol_digits)),
        }
        if direction == stupid_share.Direction.LONG:
            direction_multiplier = 1
            config_tp = symbols_tpsl[base_symbol].buy_tp
            config_is_tp_percent = symbols_tpsl[base_symbol].is_buy_tp_percent
            config_sl = symbols_tpsl[base_symbol].buy_sl
            config_is_sl_percent = symbols_tpsl[base_symbol].is_buy_sl_percent
        elif direction == stupid_share.Direction.SHORT:
            direction_multiplier = -1
            config_tp = symbols_tpsl[base_symbol].sell_tp
            config_is_tp_percent = symbols_tpsl[base_symbol].is_sell_tp_percent
            config_sl = symbols_tpsl[base_symbol].sell_sl
            config_is_sl_percent = symbols_tpsl[base_symbol].is_sell_sl_percent
        if config_tp > 0:
            if config_is_tp_percent:
                tp = round(price_target + (price_target * config_tp * direction_multiplier), symbol_digits)
                tp_mode = '{:.2f}%'.format(config_tp * 100)
            else:
                tp = round(price_target + (config_tp * symbol_point * direction_multiplier), symbol_digits)
                tp_mode = ''
            fibo_data['tp'] = tp
            fibo_data['tp_txt'] = 'TP: {} @{}'.format(tp_mode, round(tp, symbol_digits))
        else:
            fibo_data['tp'] = 0
            fibo_data['tp_txt'] = 'No TP'
        if config_sl > 0:
            if config_is_sl_percent:
                sl = round(price_target - (price_target * config_sl * direction_multiplier), symbol_digits)
                sl_mode = '{:.2f}%'.format(config_sl * 100)
            else:
                sl = round(price_target - (config_sl * symbol_point * direction_multiplier), symbol_digits)
                sl_mode = ''
            fibo_data['sl'] = sl
            fibo_data['sl_txt'] = 'SL: {} @{}'.format(sl_mode, round(sl, symbol_digits))
        else:
            fibo_data['sl'] = 0
            fibo_data['sl_txt'] = 'No SL'
    return fibo_data

async def update_trade(base_symbol, next_ticker):
    # tf = symbols_tf[base_symbol]
    await update_ohlcv(base_symbol, next_ticker)
    await trade(base_symbol)

async def update_ohlcv(base_symbol, next_ticker):
    tf = symbols_tf[base_symbol]
    symbols_trade[base_symbol] = False
    await stupid_volty_mt5.fetch_ohlcv(trade_mt5, base_symbol, tf, limit=0, timestamp=next_ticker, symbol_suffix=config.symbol_suffix)
    symbols_trade[base_symbol] = True
    # logger.debug(f'{base_symbol}::\n{stupid_volty_mt5.all_candles[base_symbol].tail(3)}')

def is_my_position(base_symbol=None, position=None, suffix=""):
    # if position["symbol"] == base_symbol and position["magic"] == magic_number:
    if base_symbol is None:
        if position is not None and position["comment"].startswith(f"{bot_prefix}{suffix}"):
            return True
    else:
        if position is not None and position["symbol"] == base_symbol and position["comment"].startswith(f"{bot_prefix}{suffix}"):
            return True
    return False

def recovery_position(position, new_price, new_lot, rw_magic_number, direction=stupid_share.Direction.LONG, step=0):
    base_symbol = position["symbol"]
    identifier = position["identifier"]
    sl = position["sl"]
    tp = position["tp"]
    if direction == stupid_share.Direction.LONG:
        modify_position(base_symbol, identifier, sl, tp, rw_magic_number)
    elif direction == stupid_share.Direction.SHORT:
        modify_position(base_symbol, identifier, sl, tp, rw_magic_number)

async def trade(base_symbol):
    try:
        if symbols_trade[base_symbol] == False:
            return
        
        tf = symbols_tf[base_symbol]
        symbol = broker_symbol(base_symbol)
        symbol_tick = mt5.symbol_info_tick(symbol)
        if symbol_tick is None:
            msg = f"{symbol} trade :: symbol_tick is None"
            logger.debug(msg)
            print(msg)
            return
        
        price_buy = symbol_tick.ask
        price_sell = symbol_tick.bid
        mid_price = (price_buy + price_sell) / 2
        
        # count position
        all_positions = positions_get(base_symbol)
        trade_count[base_symbol] = 0
        buy_count[base_symbol] = 0
        sell_count[base_symbol] = 0
        rw_count[base_symbol] = 0
        min_sell_profit = 0
        min_sell_position = None
        sell_space_pass = True
        sell_space_price = config.sell_space * mt5.symbol_info(symbol).point
        max_buy_profit = 0
        max_buy_position = None
        buy_space_pass = True
        buy_space_price = config.buy_space * mt5.symbol_info(symbol).point
        for index, position in all_positions.iterrows():
            if is_my_position(base_symbol, position, "-"):
                trade_count[base_symbol] += 1
                if position["type"] == ORDER_TYPE[1]: # sell
                    sell_count[base_symbol] += 1
                    if min_sell_profit == 0 or position["profit"] < min_sell_profit:
                        min_sell_profit = position["profit"]
                        min_sell_position = position
                    if config.sell_space > 0 and abs(position["price_open"] - price_sell) < sell_space_price:
                        # logger.debug(f"{base_symbol} trade :: sell_space = {config.sell_space} :: price space {abs(position['price_open'] - price_sell)} :: {sell_space_price}")
                        sell_space_pass = False
                elif position["type"] == ORDER_TYPE[0]: # 
                    buy_count[base_symbol] += 1
                    if max_buy_profit == 0 or position["profit"] > max_buy_profit:
                        max_buy_profit = position["profit"]
                        max_buy_position = position
                    if config.buy_space > 0 and abs(position["price_open"] - price_buy) < buy_space_price:
                        # logger.debug(f"{base_symbol} trade :: buy_space = {config.buy_space} :: price space {abs(position['price_open'] - price_buy)} :: {buy_space_price}") 
                        buy_space_pass = False
            elif is_my_position(base_symbol, position, "#RW"):
                rw_count[base_symbol] += 1

        last_signal = all_signals[base_symbol] if base_symbol in all_signals.keys() else 0
        is_long, is_short, buy_signal, sell_signal = stupid_volty_mt5.get_signal(base_symbol, config.signal_index)

        spread_factor = config.spread_factor
        price_spread = (price_buy - price_sell) * spread_factor
        signal_spread = buy_signal - sell_signal
        # ถ้า ค่าสเปรด คูณ factor มากกว่าความกว้างสัญญาณ ให้ข้าม
        if config.is_validate_spread and price_spread > signal_spread:
            print(f"{base_symbol} trade skip :: price_spread x {spread_factor}:{price_spread} > signal_spread:{signal_spread}")
            symbols_trade[base_symbol] = False
            return
        
        is_long = False
        is_short = False
        if config.is_use_midprice:
            is_long = mid_price > buy_signal and last_signal != 1
            is_short = mid_price < sell_signal and last_signal != -1
        else:
            is_long = price_buy > buy_signal and last_signal != 1
            is_short = price_sell < sell_signal and last_signal != -1
        fibo_data = None
        position_id = 0
        msg = ""
        if is_long and buy_space_pass:
            # check old position
            all_positions = positions_get(base_symbol)
            has_long_position = False
            for index, position in all_positions.iterrows():
                if is_my_position(base_symbol, position, "-"):
                    if position["type"] == ORDER_TYPE[1]:
                        if config.is_single_position:
                            logger.debug(f"[{base_symbol}] close sell position :: {position['symbol']}, {position['magic']}, {position['identifier']}")
                            all_signals[base_symbol] = 0
                            position_id = close_sell(base_symbol, position['identifier'], position['volume'], position['price_open'])
                            all_stat[base_symbol]["lot"] += position["volume"]
                            all_stat[base_symbol]["summary_profit"] += position['profit']
                            if position['profit'] > 0:
                                all_stat[base_symbol]["win"] += 1
                                all_stat[base_symbol]["last_loss"] = 0
                                # all_stat[symbol]["martingale_profit"] = 0
                            else:
                                all_stat[base_symbol]["loss"] += 1
                                all_stat[base_symbol]["last_loss"] += 1
                                # all_stat[symbol]["martingale_profit"] += position['profit']
                            notify.Send_Text(f'{base_symbol}\nWin:Loss = {all_stat[base_symbol]["win"]}:{all_stat[base_symbol]["loss"]}\nPNL = {all_stat[base_symbol]["summary_profit"]:0.2f}', True)
                    elif position["type"] == ORDER_TYPE[0]:
                        all_signals[base_symbol] = 1
                        has_long_position = True

            if buy_count[base_symbol] < config.buy_limit and (not config.is_single_position or not has_long_position):
                buy_count[base_symbol] += 1
                # calculate fibo
                price_buy = mt5.symbol_info_tick(symbol).ask
                if buy_count[base_symbol] == config.sell_limit and config.adaptive_lot == 0.0:
                    cal_lot = config.last_limit_lot
                else:
                    cal_lot = config.lot + config.adaptive_lot * (buy_count[base_symbol]-1)
                fibo_data = cal_tpsl(base_symbol, stupid_share.Direction.LONG, price_buy)
                position_id = trade_buy(base_symbol, price_buy, lot=cal_lot, tp=fibo_data['tp'], sl=fibo_data['sl'], step=buy_count[base_symbol])
                if position_id > 0:
                    all_signals[base_symbol] = 1
                symbols_trade[base_symbol] = False
                msg = f"ticket: {position_id}"
                print(msg)
            # elif buy_count[base_symbol] >= config.buy_limit:
            #     price_buy = mt5.symbol_info_tick(symbol).ask
        elif is_short and sell_space_pass:
            # check old position
            all_positions = positions_get(base_symbol)
            has_short_position = False
            for index, position in all_positions.iterrows():
                if is_my_position(base_symbol, position, "-"):
                    if position["type"] == ORDER_TYPE[0]:
                        if config.is_single_position:
                            logger.debug(f"[{base_symbol}] close buy position :: {position['symbol']}, {position['magic']}, {position['identifier']}")
                            all_signals[base_symbol] = 0
                            position_id = close_buy(base_symbol, position['identifier'], position['volume'], position['price_open'])
                            all_stat[base_symbol]["summary_profit"] += position['profit']
                            if position['profit'] > 0:
                                all_stat[base_symbol]["win"] += 1
                                all_stat[base_symbol]["last_loss"] = 0
                                # all_stat[symbol]["martingale_profit"] = 0
                            else:
                                all_stat[base_symbol]["loss"] += 1
                                all_stat[base_symbol]["last_loss"] += 1
                                # all_stat[symbol]["martingale_profit"] += position['profit']
                            notify.Send_Text(f'{base_symbol}\nWin:Loss = {all_stat[base_symbol]["win"]}:{all_stat[base_symbol]["loss"]}\nPNL = {all_stat[base_symbol]["summary_profit"]:0.2f}', True)
                    elif position["type"] == ORDER_TYPE[1]:
                        all_signals[base_symbol] = -1
                        has_short_position = True

            if sell_count[base_symbol] < config.sell_limit and (not config.is_single_position or not has_short_position):
                sell_count[base_symbol] += 1
                # calculate fibo
                price_sell = mt5.symbol_info_tick(symbol).bid
                if sell_count[base_symbol] == config.sell_limit and config.adaptive_lot == 0.0:
                    cal_lot = config.last_limit_lot
                else:
                    cal_lot = config.lot + config.adaptive_lot * (sell_count[base_symbol]-1)
                fibo_data = cal_tpsl(base_symbol, stupid_share.Direction.SHORT, price_sell)
                position_id = trade_sell(base_symbol, price_sell, lot=cal_lot, tp=fibo_data['tp'], sl=fibo_data['sl'], step=sell_count[base_symbol])
                if position_id > 0:
                    all_signals[base_symbol] = -1
                symbols_trade[base_symbol] = False
                msg = f"ticket: {position_id}"
                print(msg)
            # elif sell_count[base_symbol] >= config.sell_limit:
            #     price_sell = mt5.symbol_info_tick(symbol).bid

        rw_position_id = 0
        if rw_count[base_symbol] < config.rw_limit and (config.is_storm_helper_mode or (buy_count[base_symbol] + sell_count[base_symbol]) >= (config.buy_limit + config.sell_limit)):
            (is_rwlong, is_rwshort, signal, sto_k, sto_d) = stupid_volty_mt5.get_fongbeer_signal(base_symbol, config.signal_index, config.sto_enter_long, config.sto_enter_short)

            rw_magic_number = 0
            if len(config.rw_magic_numbers) >= rw_count[base_symbol] + 1:
                rw_magic_number = config.rw_magic_numbers[rw_count[base_symbol]]
            elif len(config.rw_magic_numbers) >= 1:
                rw_magic_number = config.rw_magic_numbers[0]

            if is_rwlong:
                logger.debug(f"[{base_symbol}] sto rw signal {signal} :: @{price_sell} :: STOCHk={sto_k}, STOCHd={sto_d}, signal={signal}")
                price_buy = mt5.symbol_info_tick(symbol).ask
                rw_count[base_symbol] += 1
                rw_step = 1 + int((config.sto_enter_long - sto_k) // config.sto_step_factor)
                cal_lot = (config.lot + config.adaptive_lot * (buy_count[base_symbol]-1)) * rw_step 
                # if min_sell_position is not None:
                #     cal_lot = min_sell_position['volume'] * 2 * rw_step
                #     # modify_position(base_symbol, min_sell_position['identifier'], 0, 0, rw_magic_number)
                #     recovery_position(min_sell_position, price_buy, cal_lot, rw_magic_number, stupid_share.Direction.LONG)
                # elif max_buy_position is not None:
                #     # modify_position(base_symbol, max_buy_position['identifier'], 0, 0, rw_magic_number)
                #     recovery_position(max_buy_position, price_buy, cal_lot, rw_magic_number, stupid_share.Direction.LONG)
                rw_position_id = trade_buy(base_symbol, price_buy, lot=cal_lot, tp=0, sl=0, magic_number=rw_magic_number, step=rw_count[base_symbol], tag="#RW")
                symbols_trade[base_symbol] = False
                msg = f"rw ticket: {rw_position_id}"
                print(msg)
            elif is_rwshort:
                logger.debug(f"[{base_symbol}] sto rw signal {signal} :: @{price_sell} :: STOCHk={sto_k}, STOCHd={sto_d}, signal={signal}")
                price_sell = mt5.symbol_info_tick(symbol).bid
                rw_count[base_symbol] += 1
                rw_step = 1 + int((sto_k - config.sto_enter_short) // config.sto_step_factor)
                cal_lot = (config.lot + config.adaptive_lot * (sell_count[base_symbol]-1)) * rw_step 
                # if max_buy_position is not None:
                #     cal_lot = max_buy_position['volume'] * 2 * rw_step
                #     # modify_position(base_symbol, max_buy_position['identifier'], 0, 0, rw_magic_number)
                #     recovery_position(max_buy_position, price_sell, cal_lot, rw_magic_number, stupid_share.Direction.SHORT)
                # elif min_sell_position is not None:
                #     # modify_position(base_symbol, min_sell_position['identifier'], 0, 0, rw_magic_number)
                #     recovery_position(min_sell_position, price_sell, cal_lot, rw_magic_number, stupid_share.Direction.SHORT)
                rw_position_id = trade_sell(base_symbol, price_sell, lot=cal_lot, tp=0, sl=0, magic_number=rw_magic_number, step=rw_count[base_symbol], tag="#RW")
                symbols_trade[base_symbol] = False
                msg = f"rw ticket: {rw_position_id}"
                print(msg)
                # if config.is_storm_helper_mode and min_profit < 0:
                #     modify_position(base_symbol, min_profit, min_profit, magic_number)
                #     pass
                
        if position_id > 0 or rw_position_id > 0:
            print(f"\r[{base_symbol}] Buy Signal : {buy_signal:5.2f}, Sell_Signal : {sell_signal:5.2f}")
            print(f"\r[{base_symbol}] Ask Price  : {price_buy:5.2f}, Bid Price   : {price_sell:5.2f}")
            logger.debug(f"[{base_symbol}] buy_count: {buy_count[base_symbol]}, sell_count: {sell_count[base_symbol]}, rw_count: {rw_count[base_symbol]}")
            logger.info(f'{base_symbol} :: is_long={is_long}, is_short={is_short}, buy_signal={buy_signal}, sell_signal={sell_signal}, price_buy={price_buy}, price_sell={price_sell}')

            if config.is_chart_mode:
                filename = ''
                if fibo_data:
                    filename = await stupid_volty_mt5.chart(base_symbol, tf, showMACDRSI=True, fiboData=fibo_data)
                else:
                    filename = await stupid_volty_mt5.chart(base_symbol, tf, showMACDRSI=True)
                notify.Send_Image(msg, image_path=filename)
            else:
                notify.Send_Text(msg)

    except Exception as ex:
        print(f"{base_symbol} found error:", type(ex).__name__, str(ex))
        logger.exception(f'trade - {base_symbol}')
        pass

async def init_symbol_ohlcv(base_symbol):
    tf = symbols_tf[base_symbol]
    logger.info(f"init_symbol_ohlcv - {base_symbol}")
    # symbol_info = mt5.symbol_info(symbol)
    # symbol_digits = symbol_info.digits
    # symbol_point = symbol_info.point
    # symbol_info_tick = mt5.symbol_info_tick(symbol)
    await stupid_volty_mt5.fetch_ohlcv(trade_mt5, base_symbol, tf, limit=stupid_volty_mt5.CANDLE_LIMIT, symbol_suffix=config.symbol_suffix)
    await stupid_volty_mt5.chart(base_symbol, tf, showMACDRSI=True)

    logger.debug(f'{base_symbol}::\n{stupid_volty_mt5.get_candle(base_symbol).tail(3)}')

def save_balance(symbols_list):
    global init_balance
    if config.is_save_balance_mode:
        account_info_dict = mt5.account_info()._asdict()
        balance = account_info_dict['balance']
        equity = account_info_dict['equity']
        balance_profit = init_balance * config.balance_profit_percent / 100.0
        if balance_profit > 0 and equity >= (init_balance + balance_profit) and balance > equity:
            for base_symbol in symbols_list:
                symbol_positions = positions_get(base_symbol)
                if len(symbol_positions) == 0:
                    logger.info(f"save_balance:: no positions")
                    return            
                for index, position in symbol_positions.iterrows():
                    close_position(position)
            old_balance = init_balance
            init_balance = mt5.account_info().balance
            cur_profit = init_balance - old_balance
            logger.info(f"save_balance:: old_balance={old_balance}, cur_profit={cur_profit}, new_balance={init_balance}")
            notify.Send_Text(f"Old Balance : {old_balance:.2f}\nProfit : {cur_profit:.2f}\nNew Balance : {init_balance:.2f}")

async def main():
    global all_stat, min_dd, init_balance
    for idx, base_symbol in enumerate(config.symbols):
        symbol = broker_symbol(base_symbol)
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            print(symbol, "not found, can not call order_check()")
            # mt5.shutdown()
            # quit()
            continue
            
        # if the symbol is unavailable in MarketWatch, add it
        if not symbol_info.visible:
            print(symbol, "is not visible, trying to switch on")
            if not mt5.symbol_select(symbol, True):
                print("symbol_select({}) failed, exit", symbol)
                # mt5.shutdown()
                # quit()
                continue

        show_bid_ask(base_symbol)
        symbols_list.append(base_symbol)
        symbols_tf[base_symbol] = config.timeframe[idx]
        symbols_trade[base_symbol] = False
        
        rw_count[base_symbol] = 0
        buy_count[base_symbol] = 0
        sell_count[base_symbol] = 0
        trade_count[base_symbol] = 0

        tpsl_dict = TPLS()
        # buy tpsl
        if config.buy_tp_str[idx].endswith('%'):
            tpsl_dict.is_buy_tp_percent = True
            tpsl_dict.buy_tp = config.p2f(config.buy_tp_str[idx])
        else:
            tpsl_dict.is_buy_tp_percent = False
            tpsl_dict.buy_tp = float(config.buy_tp_str[idx])

        if config.buy_sl_str[idx].endswith('%'):
            tpsl_dict.is_buy_sl_percent = True
            tpsl_dict.buy_sl = config.p2f(config.buy_sl_str[idx])
        else:
            tpsl_dict.is_buy_sl_percent = False
            tpsl_dict.buy_sl = float(config.buy_sl_str[idx])

        # sell tpsl
        if config.sell_tp_str[idx].endswith('%'):
            tpsl_dict.is_sell_tp_percent = True
            tpsl_dict.sell_tp = config.p2f(config.sell_tp_str[idx])
        else:
            tpsl_dict.is_sell_tp_percent = False
            tpsl_dict.sell_tp = float(config.sell_tp_str[idx])

        if config.sell_sl_str[idx].endswith('%'):
            tpsl_dict.is_sell_sl_percent = True
            tpsl_dict.sell_sl = config.p2f(config.sell_sl_str[idx])
        else:
            tpsl_dict.is_sell_sl_percent = False
            tpsl_dict.sell_sl = float(config.sell_sl_str[idx])
        
        # pnl tp
        tpsl_dict.tp_amount = float(config.tp_amount_str[idx])

        symbols_tpsl[base_symbol] = tpsl_dict
        logger.debug(f"[{base_symbol}] symbols_tpsl = {json.dumps(tpsl_dict.__dict__)}")

    logger.debug(f"symbols_tf = {symbols_tf}")
    logger.debug(f"symbols_trade = {symbols_trade}")
    
    if len(symbols_list) == 0:
        print("Empty symbols list")
        mt5.shutdown()
        exit()

    logger.debug(f"symbols_list = {symbols_list}")

    # orders = mt5.orders_total()
    # if orders > 0:
    #     print("Total orders=",orders)
    # else:
    #     print("Orders not found")

    indy_config = stupid_volty_mt5.indicator_config
    indy_config["atr_length"] = config.atr_length
    indy_config["atr_multiple"] = config.atr_multiple
    indy_config["is_confirm_macd"] = config.is_confirm_macd
    indy_config["is_macd_cross"] = config.is_macd_cross
    indy_config["is_tdv_ohlcv"] = config.is_tdv_ohlcv
    indy_config["tdv_market"] = config.tdv_market
    logger.debug(indy_config)
    stupid_volty_mt5.set_config(indy_config)

    # init all symbol ohlcv
    call_inits = [init_symbol_ohlcv(base_symbol) for base_symbol in symbols_list]
    await asyncio.gather(*call_inits)

    if config.init_balance > 0:
        init_balance = config.init_balance

    all_stat = load_json(report_json_path)
    if "init_balance" not in all_stat.keys():
        all_stat["init_balance"] = init_balance
    else:
        init_balance = all_stat["init_balance"]

    if init_balance < mt5.account_info().equity:
        init_balance = mt5.account_info().equity

    if "min_dd" not in all_stat.keys():
        all_stat["min_dd"] = 0.0
    else:
        min_dd = all_stat["min_dd"]

    # init all symbol stat
    all_positions = positions_getall(symbols_list)
    for base_symbol in symbols_list:
        if base_symbol not in all_stat.keys():
            all_stat[base_symbol] = {
                "win": 0,
                "loss": 0,
                "last_loss": 0,
                "summary_profit": 0,
                "lot": 0,
                # "trailing_stop_pips": 0,
            }
    for index, position in all_positions.iterrows():
        if is_my_position(position=position, suffix="-") and '-' in position["comment"]:
            step = int(position["comment"].split("-")[-1])
            all_stat[position['symbol']]["last_loss"] = step

    time_wait = TIMEFRAME_SECONDS['1m']
    next_tf_ticker = time.time()
    next_tf_ticker -= next_tf_ticker % time_wait

    for base_symbol in symbols_list:
        symbols_next_tf_ticker[base_symbol] = next_tf_ticker + TIMEFRAME_SECONDS[symbols_tf[base_symbol]]

    # next_tf_ticker += time_wait

    time_update = UB_TIMER_SECONDS[config.UB_TIMER_MODE]
    next_update =  time.time()
    next_update -= next_update % time_update
    next_update += time_update

    time_tick = config.TICK_TIMER
    next_tick =  time.time()
    next_tick -= next_tick % time_tick
    next_tick += time_tick
    
    while True:

        seconds = time.time()
        local_time = time.ctime(seconds)

        if seconds >= next_update:  # ครบรอบ ปรับปรุงข้อมูล
            next_update += time_update

            print(CLS_SCREEN+f"{bot_fullname}\nBot start process {local_time}")
            # print(f"Lot = {config.lot}, Buy/Sell Limit = {config.buy_limit}x{config.sell_limit}, ATR = {config.atr_length}:{config.atr_multiple}, Martingale = {'on' if config.is_martingale else 'off'}")
            print(f"Lot+Adaptive = {config.lot}+{config.adaptive_lot}, Buy:Sell:Recovery = {config.buy_limit}:{config.sell_limit}:{config.rw_limit}, ATR = {config.atr_length}:{config.atr_multiple}")
            balance_profit = round(init_balance * config.balance_profit_percent / 100.0, 2)         
            print(f"Init Balance = {init_balance:.2f}, Target = {init_balance+balance_profit:.2f}, Profit ({config.balance_profit_percent:.2f}%) = {balance_profit:.2f}")
            close_by_profit(symbols_list)

            save_balance(symbols_list)

            # prepare old position ids
            old_position_ids = []
            for index, position in all_positions.iterrows():
                if position["symbol"] in symbols_list and is_my_position(position=position):
                    old_position_ids.append(position["ticket"])
            
            # get new positions
            all_positions = positions_getall(symbols_list)

            # # update trailing stop
            # if config.is_trailing_stop:
            #     for index, position in all_positions.iterrows():
            #         if position["symbol"] in symbols_list and position["magic"] == magic_number and '-' in position["comment"]:
            #             update_trailing_stop(position)
            
            account_info_dict = mt5.account_info()._asdict()
            print(f"Balance = {account_info_dict['balance']}, Equity = {account_info_dict['equity']}, Free Margin = {account_info_dict['margin_free']}, Margin Level = {account_info_dict['margin_level']:0.2f}%")

            # check all close positions
            positions_check(all_positions, old_position_ids, account_info_dict)

            positions_report(all_positions)

        call_updates = []
        for base_symbol in symbols_list:
            # ตรวจสอบว่าถึงเวลา update ohlcv หรือยัง
            if seconds >= symbols_next_tf_ticker[base_symbol] + config.TIME_SHIFT:
                # update ohlcv
                call_updates.append(update_ohlcv(base_symbol, symbols_next_tf_ticker[base_symbol]))
                symbols_next_tf_ticker[base_symbol] += TIMEFRAME_SECONDS[symbols_tf[base_symbol]]
                print(f"[{base_symbol}] Update OHLCV : {local_time}")
        if len(call_updates) > 0:
            await asyncio.gather(*call_updates)

        # if seconds >= next_tf_ticker + config.TIME_SHIFT:  # ครบรอบ
        #     # trade all symbol
        #     call_trades = [update_ohlcv(symbol, symbols_next_tf_ticker[symbol]) for symbol in symbols_list]
        #     next_tf_ticker += time_wait

        #     await asyncio.gather(*call_trades)
            
        if seconds >= next_tick:  # ครบรอบ buy/sell tick
            next_tick += time_tick

            call_trades = [trade(base_symbol) for base_symbol in symbols_list]
            await asyncio.gather(*call_trades)

        await asyncio.sleep(1)

async def waiting():
    count = 0
    status = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    while True:
        await asyncio.sleep(1)
        print('\r'+CCYAN+CBOLD+status[count%len(status)]+' waiting...\r'+CEND, end='')
        count += 1
        count = count%len(status)

def save_to_json(filename, json_data):
    with open(filename,"w", encoding='utf8') as json_file:
        json_string = json.dumps(json_data, indent=2, ensure_ascii=False).encode('utf8')
        json_file.write(json_string.decode())
def load_json(filename):
    if os.path.exists(filename):
        with open(filename,"r", encoding='utf8') as json_file:
            return json.load(json_file)
    return {}

if __name__ == "__main__":
    try:
        pathlib.Path('./plots').mkdir(parents=True, exist_ok=True)
        pathlib.Path('./logs').mkdir(parents=True, exist_ok=True)
        pathlib.Path('./datas').mkdir(parents=True, exist_ok=True)

        report_json_path = './datas/orders_report.json'

        logger = logging.getLogger(__name__)
        logger.setLevel(config.LOG_LEVEL)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler = RotatingFileHandler('./logs/app.log', maxBytes=250000, backupCount=10)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        logger.info(f"===== Start :: {bot_name} =====")

        if os.path.exists(mt5_path):
            logger.debug(f"MT5 folder: {mt5_path}")
            mt5.initialize(path=mt5_path)
        else:
            mt5.initialize() #Open terminal MT5

        terminal_info_dict = mt5.terminal_info()._asdict()
        mt5_df=pd.DataFrame(list(terminal_info_dict.items()),columns=['property','value'])
        logger.debug("terminal_info() as dataframe:")
        logger.debug(f"\n{mt5_df}")

        # display data on the MetaTrader 5 package
        print("MetaTrader5 package author: ", mt5.__author__)
        print("MetaTrader5 package version: ", mt5.__version__)

        trade_mt5 = mt5.login(login=int(user_id), server=server_user, password=password_user) # Login
        if trade_mt5:
            #print(mt5.account_info())#information from server
            account_info_dict = mt5.account_info()._asdict() # information() to {}
            print(account_info_dict)
            account_info_list = list(account_info_dict.items()) # Change {} to list
            #print(account_info_list)
            #df=pd.DataFrame(account_info_list,columns=['property','value'])#Convert list to data list table
            #print(df)
        else:
            print("No Connect: Login Failed")
            exit()
        
        os.system("color") # enables ansi escape characters in terminal
        print(HIDE_CURSOR, end="")
        loop = asyncio.get_event_loop()
        # แสดง status waiting ระหว่างที่รอ...
        loop.create_task(waiting())
        loop.run_until_complete(main())

    except KeyboardInterrupt:
        save_to_json(report_json_path, all_stat)
        print(CLS_LINE+'\rbye')

    except Exception as ex:
        print(type(ex).__name__, str(ex))
        logger.exception('app')
        notify.Send_Text(f'{bot_name} bot stop')

    finally:
        print(SHOW_CURSOR, end="")