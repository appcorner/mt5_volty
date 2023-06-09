# -*- coding: utf-8 -*-

import MetaTrader5 as mt5
import pandas as pd
import pandas_ta as ta
import mplfinance as mpf
import matplotlib.pyplot as plt
import numpy as np
import pytz
import time
from datetime import datetime
from tvDatafeed import TvDatafeed, Interval

import logging
logger = logging.getLogger('__main__')

tv = TvDatafeed()

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
TIMEFRAME_MT5 = {
    '1m': mt5.TIMEFRAME_M1,
    '3m': mt5.TIMEFRAME_M3,
    '5m': mt5.TIMEFRAME_M5,
    '15m': mt5.TIMEFRAME_M15,
    '30m': mt5.TIMEFRAME_M30,
    '1h': mt5.TIMEFRAME_H1,
    '2h': mt5.TIMEFRAME_H2,
    '4h': mt5.TIMEFRAME_H4,
    '6h': mt5.TIMEFRAME_H6,
    '8h': mt5.TIMEFRAME_H8,
    '12h': mt5.TIMEFRAME_H12,
    '1d': mt5.TIMEFRAME_D1,
}

TDV_MARGET = 'OANDA'
TIMEFRAME_TDV = {
    '1m': Interval.in_1_minute,
    '3m': Interval.in_3_minute,
    '5m': Interval.in_5_minute,
    '15m': Interval.in_15_minute,
    '30m': Interval.in_30_minute,
    '1h': Interval.in_1_hour,
    '2h': Interval.in_2_hour,
    '4h': Interval.in_4_hour,
    '6h': "6H",
    '8h': "8H",
    '12h': "12H",
    '1d': Interval.in_daily,
}

TZ_ADJUST = 7
MT_ADJUST = 4

CANDLE_LIMIT = 200
CANDLE_PLOT = 100
CANDLE_SAVE = CANDLE_PLOT + 100

all_candles = {}

indicator_config = {
    "RSI_PERIOD": 14,
    "MACD_FAST": 12,
    "MACD_SLOW": 26,
    "MACD_SIGNAL": 9,
    "atr_length": 4,
    "atr_multiple": 0.75,
    "is_confirm_macd": False,
    "is_macd_cross": False,
}

def nz(value, default):
	return default if pd.isnull(value) else value
def na(value):
    return pd.isnull(value)

def set_config(config):
    global indicator_config
    for key in indicator_config.keys():
        if key in config.keys():
            indicator_config[key] = config[key]

def set_indicator(symbol, bars, config=indicator_config):
    # df = pd.DataFrame(
    #     bars, columns=["time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"]
    # )
    # df["time"] = pd.to_datetime(df["time"], unit="s").map(
    #     lambda x: (x+pd.Timedelta(hours=MT_ADJUST))
    # )
    # # df["time"] = pd.to_datetime(df["time"], unit="s")
    # df = df.set_index("time")
    # df.rename({'tick_volume': 'volume'}, axis=1, inplace=True)
    df = bars.copy()

    # เอาข้อมูลใหม่ไปต่อท้าย ข้อมูลที่มีอยู่
    if symbol in all_candles.keys() and len(df) < CANDLE_LIMIT:
        df = pd.concat([all_candles[symbol], df], ignore_index=False)

        # เอาแท่งซ้ำออก เหลืออันใหม่สุด
        df = df[~df.index.duplicated(keep='last')].tail(CANDLE_LIMIT)

    df = df.tail(CANDLE_LIMIT)

    if len(df) < CANDLE_SAVE:
        print(f'less candles for {symbol}, skip add_indicator')
        return df
    
    # คำนวนค่าต่างๆใหม่
    df['MACD'] = 0
    df['MACDs'] = 0
    df['MACDh'] = 0
    df["RSI"] = 0

    try:

        # //@version=5
        # strategy("X48-Strategy | Volty Expan Close Strategy | V.Forex", overlay=true, initial_capital=1000)
        # length = input(5)
        # numATRs = input(0.75)
        # atrs = ta.sma(ta.tr, length)*numATRs
        # if (not na(close[length]))
        #  strategy.entry("VltClsLE", strategy.long, stop=close+atrs, comment = "🌙")
        #  strategy.entry("VltClsSE", strategy.short, stop=close-atrs, comment = "👻")
        # plot(atrs, "ATR", color = color.red, linewidth = 2, style = plot.style_line)
        # //plot(strategy.equity, title="equity", color=color.red, linewidth=2, style=plot.style_areabr)
        # //===================== เรียกใช้  library =========================
        # import X4815162342/X48_LibaryStrategyStatus/2 as fuLi 
        # //แสดงผล Backtest

        # show_Net = input.bool(true,'Monitor Profit&Loss', inline = 'Lnet', group = '= PNL MONITOR SETTING =')
        # position_ = input.string('bottom_center','Position', options = ['top_right','middle_right','bottom_right','top_center','middle_center','bottom_center','middle_left','bottom_left'] , inline = 'Lnet')
        # size_i = input.string('auto','size', options = ['auto','tiny','small','normal'] , inline = 'Lnet') 
        # color_Net = input.color(color.blue,"" , inline = 'Lnet')
        # fuLi.NetProfit_Show(show_Net , position_ , size_i,  color_Net )

        length = config['atr_length']
        numATRs = config['atr_multiple']

        # df['ema'] = ta.ema(df['close'],emaPer)
        df['tr'] = ta.true_range(df.high, df.low, df.close)
        df['atrs'] = ta.sma(df.tr, length) * numATRs

        atrs_value = df['atrs'].shift()
        last_close = df['close'].shift()
        df['buy_signal'] = last_close + atrs_value
        df['sell_signal'] = last_close - atrs_value

        # cal MACD
        ewm_fast     = df['close'].ewm(span=config['MACD_FAST'], adjust=False).mean()
        ewm_slow     = df['close'].ewm(span=config['MACD_SLOW'], adjust=False).mean()
        df['MACD']   = ewm_fast - ewm_slow
        df['MACDs']  = df['MACD'].ewm(span=config['MACD_SIGNAL']).mean()
        df['MACDh']  = df['MACD'] - df['MACDs']

        # cal RSI
        df["RSI"] = ta.rsi(df['close'],config['RSI_PERIOD'])

    except Exception as ex:
        print(type(ex).__name__, symbol, str(ex))
        logger.error(ex)

    return df

"""
fetch_ohlcv - อ่านแท่งเทียน
exchange: mt5 connect
symbol: coins symbol
timeframe: candle time frame
limit: จำนวนแท่งที่ต้องการ, ใส่ 0 หากต้องการให้เอาแท่งใหม่ที่ไม่มาครบ
timestamp: ระบุเวลาปัจจุบัน ถ้า limit=0
"""
async def fetch_ohlcv(exchange, symbol, timeframe, limit=CANDLE_LIMIT, timestamp=0, config=indicator_config):
    global all_candles
    if not exchange:
        print("No MT5 Connect")
        return
    try:
        # กำหนดการอ่านแท่งเทียนแบบไม่ระบุจำนวน
        if limit == 0 and symbol in all_candles.keys():
            timeframe_secs = TIMEFRAME_SECONDS[timeframe]
            ts_adjust_secs = TZ_ADJUST*60*60
            last_candle_time = int(pd.Timestamp(all_candles[symbol].index[-1]).timestamp()) - ts_adjust_secs
            # ให้อ่านแท่งสำรองเพิ่มอีก 2 แท่ง
            cal_limit = round(1.5+(timestamp-last_candle_time)/timeframe_secs)
            limit = cal_limit if cal_limit < CANDLE_LIMIT else CANDLE_LIMIT
            logger.debug(f"fetch_ohlcv {symbol} {timestamp} {last_candle_time} {timestamp-last_candle_time} {ts_adjust_secs} {cal_limit} {limit}")
            
        # ohlcv_bars  = mt5.copy_rates_from_pos(symbol, TIMEFRAME_MT5[timeframe], 0, limit)
        ohlcv_bars = tv.get_hist(symbol,TDV_MARGET,TIMEFRAME_TDV[timeframe],limit)
        # ohlcv_bars['symbol'] = ohlcv_bars['symbol'].apply(lambda x: x[x.find(':')+1:])
        logger.info(f"{symbol} fetch_ohlcv, limit:{limit}, len:{len(ohlcv_bars)}")
        if len(ohlcv_bars):
            all_candles[symbol] = set_indicator(symbol, ohlcv_bars, config=config)
    except Exception as ex:
        print(type(ex).__name__, symbol, str(ex))
        if limit == 0 and symbol in all_candles.keys():
            print('----->', timestamp, last_candle_time, timestamp-last_candle_time, round(1.5+(timestamp-last_candle_time)/timeframe_secs))
        # if '"code":-1130' in str(ex):
        #     watch_list.remove(symbol)
        #     print(f'{symbol} is removed from watch_list')

def get_signal(symbol, idx, config=indicator_config):
    df = all_candles[symbol]
    is_long = False
    is_short = False

    # atrs_value = df['atrs'][idx-1]
    # last_close = df['close'][idx-1]
    # buy_signal = last_close + atrs_value
    # sell_signal = last_close - atrs_value
    buy_signal = df['buy_signal'][idx]
    sell_signal = df['sell_signal'][idx]

    if df['high'][idx] > buy_signal:
        is_long = True
    elif df['low'][idx] < sell_signal:
        is_short = True

    return is_long, is_short, buy_signal, sell_signal

async def chart(symbol, timeframe, config=indicator_config, showMACDRSI=False, fiboData=None):
    filename = f"./plots/order_{str(symbol).lower()}.png"
    try:
        print(f"{symbol} create line_chart")
        df = all_candles[symbol]
        data = df.tail(CANDLE_PLOT)

        showFibo = fiboData != None

        gap = (max(data['high']) - min(data['low'])) * 0.1
        # print(gap)

        long_markers = []
        short_markers = []
        has_long = False
        has_short = False

        last_signal = 0
        for i in range(len(data)):
            long_markers.append(np.nan)
            short_markers.append(np.nan)
            is_long, is_short, buy_signal, sell_signal = get_signal(symbol, CANDLE_PLOT+i, config)
            if is_long and last_signal != 1:
                has_long = True
                last_signal = 1
                long_markers[i] = data['low'][i] - gap
            elif is_short and last_signal != -1:
                has_short = True
                last_signal = -1
                short_markers[i] = data['high'][i] + gap

        added_plots = [
            mpf.make_addplot(data['buy_signal'],color='green',width=.5),
            mpf.make_addplot(data['sell_signal'],color='red',width=.5),
        ]
        if has_long:
            added_plots.append(mpf.make_addplot(long_markers, type='scatter', marker='^', markersize=100, color='green',panel=0))
        if has_short:
            added_plots.append(mpf.make_addplot(short_markers, type='scatter', marker='v', markersize=100, color='red',panel=0))
 
        if showMACDRSI:
            rsi30 = [30 for i in range(0, CANDLE_PLOT)]
            rsi50 = [50 for i in range(0, CANDLE_PLOT)]
            rsi70 = [70 for i in range(0, CANDLE_PLOT)]
            added_plots += [ 
                mpf.make_addplot(data['RSI'],ylim=(10, 90),panel=2,color='blue',width=0.75,
                    ylabel=f"RSI ({config['RSI_PERIOD']})", y_on_right=False),
                mpf.make_addplot(rsi30,ylim=(10, 90),panel=2,color='red',linestyle='-.',width=0.5),
                mpf.make_addplot(rsi50,ylim=(10, 90),panel=2,color='red',linestyle='-.',width=0.5),
                mpf.make_addplot(rsi70,ylim=(10, 90),panel=2,color='red',linestyle='-.',width=0.5),
            ]
            colors = ['green' if value >= 0 else 'red' for value in data['MACDh']]
            added_plots += [
                mpf.make_addplot(data['MACDh'],type='bar',width=0.5,panel=3,color=colors,
                    ylabel=f"MACD ({config['MACD_FAST']})", y_on_right=True),
                mpf.make_addplot(data['MACD'],panel=3,color='orange',width=0.75),
                mpf.make_addplot(data['MACDs'],panel=3,color='blue',width=0.75),
            ]

        kwargs = dict(
            figscale=1.2,
            figratio=(8, 7),
            panel_ratios=(8,2,2,2) if showMACDRSI else (4,1),
            addplot=added_plots,
            scale_padding={'left': 0.5, 'top': 0.6, 'right': 1.0, 'bottom': 0.5},
            )
        
        fibo_title = ''

        if showFibo:
            logger.debug(f"{symbol} {fiboData}")

            tpsl_colors = []
            tpsl_data = []
            if 'tp' in fiboData.keys() and fiboData['tp'] > 0:
                tpsl_colors.append('g')
                tpsl_data.append(fiboData['tp'])
            if 'sl' in fiboData.keys() and fiboData['sl'] > 0:
                tpsl_colors.append('r')
                tpsl_data.append(fiboData['sl'])
            if 'price' in fiboData.keys():
                tpsl_colors.append('b')
                tpsl_data.append(fiboData['price'])
            if len(tpsl_data) > 0:
                tpsl_lines = dict(
                    hlines=tpsl_data,
                    colors=tpsl_colors,
                    alpha=0.5,
                    linestyle='-.',
                    linewidths=1,
                    )
                kwargs['hlines']=tpsl_lines

            if 'min_max' in fiboData.keys():
                minmax_lines = dict(
                    alines=fiboData['min_max'],
                    colors='black',
                    linestyle='--',
                    linewidths=0.1,
                    )
                kwargs['alines']=minmax_lines

            if 'fibo_type' in fiboData.keys():
                fibo_title = ' fibo-'+fiboData['fibo_type'][0:2]

        myrcparams = {'axes.labelsize':10,'xtick.labelsize':8,'ytick.labelsize':8}
        mystyle = mpf.make_mpf_style(base_mpf_style='charles',rc=myrcparams)

        title = f'{symbol} :: Volty :: ({timeframe} @ {data.index[-1]}){fibo_title}'
        print(title)

        fig, axlist = mpf.plot(
            data,
            volume=True,volume_panel=1,
            **kwargs,
            type="candle",
            xrotation=0,
            ylabel='Price',
            style=mystyle,
            returnfig=True,
            # axtitle=title,
        )
        ax1,*_ = axlist

        title = ax1.set_title(f'{title}{fibo_title})')
        title.set_fontsize(14)

        if showFibo:
            if 'difference' in fiboData.keys():
                difference = fiboData['difference']
            else:
                difference = 0.0
            if 'fibo_levels' in fiboData.keys():
                fibo_colors = ['red','brown','orange','gold','green','blue','gray','purple','purple','purple']
                fibo_levels = fiboData['fibo_levels']
                for idx, fibo_val in enumerate(fiboData['fibo_values']):
                    if idx < len(fibo_levels)-1:
                        ax1.fill_between([0, CANDLE_PLOT] ,fibo_levels[idx],fibo_levels[idx+1],color=fibo_colors[idx],alpha=0.1)
                    ax1.text(0,fibo_levels[idx] + difference * 0.02,f'{fibo_val}({fibo_levels[idx]:.2f})',fontsize=8,color=fibo_colors[idx],horizontalalignment='left')

            none_tpsl_txt = []
            if 'tp' in fiboData.keys() and fiboData['tp'] > 0:
                fibo_tp = fiboData['tp']
                fibo_tp_txt = fiboData['tp_txt']
                ax1.text(CANDLE_PLOT,fibo_tp - difference * 0.06,fibo_tp_txt,fontsize=8,color='g',horizontalalignment='right')
            else:
                none_tpsl_txt.append('No TP')

            if 'sl' in fiboData.keys() and fiboData['sl'] > 0:
                fibo_sl = fiboData['sl']
                fibo_sl_txt = fiboData['sl_txt']
                ax1.text(CANDLE_PLOT,fibo_sl - difference * 0.06,fibo_sl_txt,fontsize=8,color='r',horizontalalignment='right')
            else:
                none_tpsl_txt.append('No SL')
                
            if 'price' in fiboData.keys():
                fibo_price = fiboData['price']
                fibo_price_txt = fiboData['price_txt'] + (' [' + ','.join(none_tpsl_txt) + ']' if len(none_tpsl_txt) > 0 else '')
                ax1.text(CANDLE_PLOT,fibo_price - difference * 0.06,fibo_price_txt,fontsize=8,color='b',horizontalalignment='right')

        fig.savefig(filename)

        plt.close(fig)

        # open(plot_file, 'rb')

    except Exception as ex:
        print(type(ex).__name__, symbol, str(ex))

    return filename