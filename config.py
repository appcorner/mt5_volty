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

def get_list_int(group, name, default=[]):
    value = default
    try:
        if is_exist(group, name):
            value = [int(x.strip()) for x in config[group][name].split(',')]
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
PATH = get_str('mt5','path')
symbol_suffix = get_str('mt5','symbol_suffix')
is_tdv_ohlcv = get_str('mt5','tdv_ohlcv', 'off') == 'on'
tdv_market = get_str('mt5','tdv_market', 'OANDA')

#------------------------------------------------------------
# line
#------------------------------------------------------------
LINE_NOTIFY_TOKEN = get_str('line','notify_token')
is_chart_mode = get_str('line','chart_mode', 'off') == 'on'

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

init_balance = get_float('setting', 'init_balance', 0.0)
is_save_balance_mode = get_str('setting', 'save_balance_mode', 'off') == 'on'
balance_profit_percent = get_float('setting', 'balance_profit_percent', 5.0)
dd_alert_percent = get_float('setting', 'dd_alert_percent', 50.0)

trade_limit = get_int('setting', 'trade_limit', 1)
buy_limit = get_int('setting', 'buy_limit', 1)
sell_limit = get_int('setting', 'sell_limit', 1)
buy_space = get_int('setting', 'order_space', 100)
sell_space = get_int('setting', 'order_space', 100)
is_single_position = get_str('setting', 'single_position', 'off') == 'on'

rw_limit = get_int('setting', 'rw_limit', 1)
rw_magic_numbers = get_list_int('setting', 'rw_magic_numbers', [6689])
is_storm_helper_mode = get_str('setting', 'storm_helper_mode', 'off') == 'on'
last_limit_lot = get_float('setting', 'last_limit_lot', 0.01)

# symbol = get_str('setting', 'symbol', 'XAUUSD')
symbols = get_list('setting', 'symbols', ['XAUUSD'])
lot = get_float('setting', 'lot', 0.01)
deviation = get_int('setting', 'deviation', 20)
is_use_midprice = get_str('setting', 'use_midprice', 'off') == 'on'
spread_factor = get_float('setting', 'spread_factor', 2.0)
is_validate_spread = get_str('setting', 'validate_spread', 'off') == 'on'

atr_length = get_int('setting', 'atr_length', 100)
atr_multiple = get_float('setting', 'atr_multiple', 0.75)

sto_enter_long = get_float('setting', 'sto_enter_long', 30.0)
sto_enter_short = get_float('setting', 'sto_enter_short', 70.0)
sto_step_factor = get_float('setting', 'sto_step_factor', 10)

is_confirm_macd = get_str('setting', 'confirm_macd', 'off') == 'on'
is_macd_cross = get_str('setting', 'macd_cross', 'off') == 'on'

is_martingale = get_str('setting', 'martingale_mode', 'off') == 'on'
martingale_factor = get_float('setting', 'martingale_factor', 2.0)
martingale_max = get_int('setting', 'martingale_max', 8)

is_auto_tpsl = get_str('setting', 'auto_tpsl', 'off') == 'on'

buy_tp_str = get_list('setting', 'buy_tp', ['15'])
sell_tp_str = get_list('setting', 'sell_tp', ['0'])

buy_sl_str = get_list('setting', 'buy_sl', ['15'])
sell_sl_str = get_list('setting', 'sell_sl', ['0'])

tp_amount_str = get_list('setting', 'tp_amount', ['0.5'])

# is_trailing_profit = get_str('setting', 'trailing_profit', 'on') == 'on'
is_trailing_stop = get_str('setting', 'trailing_stop', 'on') == 'on'