import configparser

def is_exist(group, name):
    return group in config.keys() and name in config[group].keys()

def get_list(group, name, default=[]):
    value = default
    try:
        if is_exist(group, name):
            value = [x.strip() for x in config[group][name].split(',')]
        else:
            print(f'config {group}.{name} not found, set default to {default}')
    except Exception as ex:
        print(type(ex).__name__, str(ex))
        print(f'config {group}.{name} not found, set default to {default}')
    return value

def get_list_float(group, name, default=[]):
    value = default
    try:
        if is_exist(group, name):
            value = [float(x.strip()) for x in config[group][name].split(',')]
        else:
            print(f'config {group}.{name} not found, set default to {default}')
    except Exception as ex:
        print(type(ex).__name__, str(ex))
        print(f'config {group}.{name} not found, set default to {default}')
    return value
    
def get_str(group, name, default=''):
    value = default
    try:
        if is_exist(group, name):
            value = config[group][name]
        else:
            print(f'config {group}.{name} not found, set default to {default}')
    except Exception as ex:
        print(type(ex).__name__, str(ex))
        print(f'config {group}.{name} not found, set default to {default}')
    return value

def get_int(group, name, default=0):
    value = default
    try:
        if is_exist(group, name):
            value = int(config[group][name])
        else:
            print(f'config {group}.{name} not found, set default to {default}')
    except Exception as ex:
        print(type(ex).__name__, str(ex))
        print(f'config {group}.{name} not found, set default to {default}')
    return value

def get_float(group, name, default=0.0):
    value = default
    try:
        if is_exist(group, name):
            value = float(config[group][name])
        else:
            print(f'config {group}.{name} not found, set default to {default}')
    except Exception as ex:
        print(type(ex).__name__, str(ex))
        print(f'config {group}.{name} not found, set default to {default}')
    return value

def p2f(x):
    return float(x.strip('%'))/100

config = configparser.ConfigParser(interpolation=None)
config.optionxform = str
config_file = open("config.ini", mode='r', encoding='utf-8-sig')
config.readfp(config_file)

#------------------------------------------------------------
# MT5
#------------------------------------------------------------
LOGIN = get_str('mt5','login')
PASSWORD = get_str('mt5','password')
SERVER = get_str('mt5','server')

#------------------------------------------------------------
# line
#------------------------------------------------------------
LINE_NOTIFY_TOKEN = get_str('line','notify_token')

#------------------------------------------------------------
# app_config
#------------------------------------------------------------
TIME_SHIFT = get_int('app_config', 'TIME_SHIFT', 5)
# CANDLE_LIMIT = get_int('app_config', 'CANDLE_LIMIT', 1000)
# CANDLE_PLOT = get_int('app_config', 'CANDLE_PLOT', 100)
LOG_LEVEL = get_int('app_config', 'LOG_LEVEL', 20)
UB_TIMER_MODE = get_int('app_config', 'UB_TIMER_MODE', 2)
if UB_TIMER_MODE < 0 or UB_TIMER_MODE > 6:
    UB_TIMER_MODE = 2
TICK_TIMER = get_int('app_config', 'TICK_TIMER', 5)
# SWING_TF = get_int('app_config', 'SWING_TF', 5)
# SWING_TEST = get_int('app_config', 'SWING_TEST', 2)
# TP_FIBO = get_int('app_config', 'TP_FIBO', 2)

#------------------------------------------------------------
# setting
#------------------------------------------------------------
# timeframe = get_str('setting', 'timeframe', '5m')
timeframe = get_list('setting', 'timeframe', ['5m'])
signal_index = get_int('setting', 'signal_index', -2)
magic_number = get_int('setting', 'magic_number', '999111')

# symbol = get_str('setting', 'symbol', 'XAUUSD')
symbols = get_list('setting', 'symbols', ['XAUUSD'])
lot = get_float('setting', 'lot', 0.01)
deviation = get_int('setting', 'deviation', 20)

atr_length = get_int('setting', 'atr_length', 100)
atr_multiple = get_float('setting', 'atr_multiple', 0.75)

is_confirm_macd = get_str('setting', 'confirm_macd', 'on') == 'on'
is_macd_cross = get_str('setting', 'macd_cross', 'off') == 'on'

is_martingale = get_str('setting', 'martingale_mode', 'off') == 'on'
martingale_factor = get_float('setting', 'martingale_factor', 2.0)
martingale_max = get_int('setting', 'martingale_max', 8)

is_auto_tpsl = get_str('setting', 'auto_tpsl', 'on') == 'on'

buy_sl_str = get_str('setting', 'buy_sl', '').strip()
if buy_sl_str.endswith('%'):
    is_buy_sl_percent = True
    buy_sl = p2f(buy_sl_str)
else:
    is_buy_sl_percent = False
    buy_sl = get_int('setting', 'buy_sl', 500)
    
buy_tp_str = get_str('setting', 'buy_tp', '').strip()
if buy_tp_str.endswith('%'):
    is_buy_tp_percent = True
    buy_tp = p2f(buy_tp_str)
else:
    is_buy_tp_percent = False
    buy_tp = get_int('setting', 'buy_tp', 1500)

sell_sl_str = get_str('setting', 'sell_sl', '').strip()
if sell_sl_str.endswith('%'):
    is_sell_sl_percent = True
    sell_sl = p2f(sell_sl_str)
else:
    is_sell_sl_percent = False
    sell_sl = get_int('setting', 'sell_sl', 500)
    
sell_tp_str = get_str('setting', 'sell_tp', '').strip()
if sell_tp_str.endswith('%'):
    is_sell_tp_percent = True
    sell_tp = p2f(sell_tp_str)
else:
    is_sell_tp_percent = False
    sell_tp = get_int('setting', 'sell_tp', 1500)

# is_trailing_profit = get_str('setting', 'trailing_profit', 'on') == 'on'
is_trailing_stop = get_str('setting', 'trailing_stop', 'on') == 'on'