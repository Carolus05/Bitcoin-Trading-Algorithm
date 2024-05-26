import pandas as pd
from binance.client import Client
import numpy as np
from datetime import datetime, timedelta
import math
import sys
import time

"""
enviorment variables used to connect to exchnage and keep track of trades through exchange api
"""

keyspath: str = ''
api_key: str = ''
secret_key: str = ''

def extract_keys(path:str): # extract api keys from textfile
    with open(path, 'r') as f:
        api_key = f.readline().strip()
        secret_key = f.readline().strip()
        return api_key, secret_key

# api_key, secret_key = extract_keys(path=keyspath)

def Instantiate_Client(api_key:str, secret_key:str):
    try:
        client = Client(api_key=api_key, api_secret=secret_key)
    except Exception as e:
        print(f'client instantiated unsuccessfully. Error - {e}')
        sys.exit()
    print('Client successfully instantiated.')
    return client

client = Instantiate_Client(api_key=api_key, secret_key=secret_key)

"""
Customization variables for user preferences
"""
# vars
"""
investment amount must be gretaer or equal to  10 US dollars equivalent of 10 of the prefered stable coin
"""

perc: int = 100  # percentage of account capital to use for trade size
stable: str = 'USDT' # trading stable coin, what asset to use as trading capital

days: int = 365*3 # number of days to extract historical data for
weeks: int = round(days/7)

Assets: list[str] = ['BTC'] # Ticker for Bitcoin
CandleStick_interval : list[str] = ['1d', '1w'] # candlestick intervals needed to calculate MACD values

day_interval: str = CandleStick_interval[0]
week_interval: str = CandleStick_interval[1]

num_days: int = 365 # run for x num of days
timertime : int= 86400 * num_days # 24 hours x 365 days 

def calculate_investment(stable:str, perc:int) -> float:  
    # calculates investment based on percentage of account balance you want to use as investment capital
    try:
        balance = client.get_asset_balance(asset=stable)
        balance: float = float(balance['free'])
    except Exception as e:
        print(f'Unable to retrieve account balance. Error - {e}')
        sys.exit()
    print(f'{stable} Balance: {balance:.2f}')
    return perc/100 * balance

def Check_Exchange(assets:list[str]) -> None:  # check if data availible for assets
    if len(assets) > 1:
        for i in range(len(assets)):
            if client.get_symbol_info(symbol=assets[i]):
                time.sleep(1)
            else:
                index = assets.index(i)
                del assets[index]

        if len(assets) == 0:
            sys.exit()
        else:
            return assets
    else:
        return assets

Assets = Check_Exchange(assets=Assets)

def add_stablecoin(assets:list[str], stablecoin:str) -> list[str]:
    Assets_with_stablecoin: list = [asset + stablecoin for asset in assets]
    return Assets_with_stablecoin

coins = add_stablecoin(assets=Assets, stablecoin=stable) # list of trading pairs
print(coins)

def Market_Buy(asset:str, qty:float) -> dict:  # place market_buy order with params
    # buy asset at current availible price, not limit order
    try:
        order = client.order_market_buy(symbol=asset, quantity=qty)
    except Exception as e:
        print(f'Failed to place order. Error - {e}')
        sys.exit()

    while True:
        try:
            orderstatus = client.get_order(symbol=asset, orderId=order['orderId'])
        except Exception as e:
            print(f'Could not get order information. Error - {e}')
            print('Exit position manually.')
            sys.exit()

        if orderstatus['status'] == 'FILLED':
            break   
    return order

def Market_Sell(asset:str, qty:float) -> dict:  # place market_sell order with params
    # sell asset at current availible price, not limit order
    try:
        order = client.order_market_sell(symbol=asset, quantity=qty)
    except Exception as e:
        print(f'Failed to place order. Error - {e}')
        print('Exit position manually.')
        sys.exit()

    while True:
        try:
            orderstatus = client.get_order(symbol=asset, orderId=order['orderId'])
        except Exception as e:
            print(f'Could not get order information. Error - {e}')
            sys.exit()
        
        if orderstatus['status'] == 'FILLED':
            break
    return order

def daily_data(symbol_id: str, interval: str, day: int) -> pd.DataFrame:
    try:
        # Use datetime objects for date calculations
        end_date = datetime.utcnow()  # Current UTC time
        start_date = end_date - timedelta(days=day)
        # Format dates for Binance API request
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        # Request historical klines directly with a specified start and end time
        historical_data = client.get_historical_klines(symbol_id, interval=interval, start_str=start_str, end_str=end_str)
        # Create DataFrame directly from the list of klines
        frame = pd.DataFrame(historical_data)
        frame = frame.iloc[:, :6]
        frame.columns = ['Time', 'Open', 'High', 'Low', 'Close', 'Volume']
        frame.set_index('Time', inplace=True)
        frame.index = pd.to_datetime(frame.index, unit='ms')
        frame = frame.astype(float)
        return frame

    except Exception as e:
        # Handle exceptions gracefully and print an error message
        print(f"Error fetching data for {symbol_id}. Error - {e}")
        return pd.DataFrame()  # Return an empty DataFrame in case of an error

def weekly_data(symbol_id: str, interval: str, weeks: int) -> pd.DataFrame:
    try:
        # Use datetime objects for date calculations
        end_date = datetime.utcnow()  # Current UTC time
        start_date = end_date - timedelta(weeks=weeks)
        # Format dates for Binance API request
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        # Request historical klines directly with a specified start and end time
        historical_data = client.get_historical_klines(symbol_id, interval=interval, start_str=start_str, end_str=end_str)
        # Create DataFrame directly from the list of klines
        frame = pd.DataFrame(historical_data)
        frame = frame.iloc[:, :6]
        frame.columns = ['Time', 'Open', 'High', 'Low', 'Close', 'Volume']
        frame.set_index('Time', inplace=True)
        frame.index = pd.to_datetime(frame.index, unit='ms')
        frame = frame.astype(float)
        return frame

    except Exception as e:
        # Handle exceptions gracefully and print an error message
        print(f"Error fetching data for {symbol_id}. Error - {e}")
        return pd.DataFrame()  # Return an empty DataFrame in case of an error

def quantitycalc(symbol_id:str, investment:float) -> float:  # calculate quantity of investment
    try:
        ticker: dict = client.get_symbol_ticker(symbol=symbol_id)
    except Exception as e:
        # re-establish the connection and retry the request
        client.connect()
        ticker: dict = client.get_symbol_ticker(symbol=symbol_id)
    price: float = float(ticker['price'])
    qty: float = investment / price
    return qty

def add_technicals(data) -> pd.DataFrame:
    # functions for technical indicators MACD, calculated based on df 

    def add_MACD(data) -> pd.DataFrame:
        Longer_Len: int = 26
        Shorter_Len: int = 12
        Signal_Len: int = 9

        # Calculate the 12-period EMA
        data['EMA12'] = data['Close'].ewm(span=Shorter_Len, adjust=False).mean()
        # Calculate the 26-period EMA
        data['EMA26'] = data['Close'].ewm(span=Longer_Len, adjust=False).mean()
        # Calculate MACD (the difference between 12-period EMA and 26-period EMA)
        data['MACD'] = data['EMA12'] - data['EMA26']
        # Calculate the 9-period EMA of MACD (Signal Line)
        data['Signal_Line'] = data['MACD'].ewm(span=Signal_Len, adjust=False).mean()

        return data
    
    data = add_MACD(data=data)

    # irrelevant for strategy
    MA_length: int = 20
    data['Vol_MA'] = data.Volume.rolling(window=MA_length).mean()
    data['average_price'] = (data['Open'] + data['High'] + data['Low'] + data['Close']) / 4
    data.dropna(inplace=True)
    return data

def get_daily_data(asset:str, interval:str, day:int) -> pd.DataFrame:
    df = daily_data(symbol_id=asset, interval=interval, day=day)
    df = add_technicals(data=df)
    # add indicators on daily timeframe to calculate market sentiment
    df['200D_SMA'] = df.Close.rolling(window=200).mean()
    df['50D_SMA'] = df.Close.rolling(window=50).mean()
    return df

def get_weekly_data(asset: str, interval: str, weeks: int):
    df = weekly_data(symbol_id=asset, interval=interval, weeks=weeks)
    df = add_technicals(data=df)
    return df

def Visualize(symbol_id, df):
    from lightweight_charts import Chart
    df = df.iloc[:, :6] 
    df = df.tail(200)
    chart = Chart()

    def take_screenshot(key):
        img = chart.screenshot()
        t = time.time()

        with open(f"screenshot-{str(t)}.png", 'wb') as f:
            f.write(img)
            print("\n screenshot saved.\n")

    chart.grid(vert_enabled = True, horz_enabled = True)
    
    chart.layout(background_color='#000000', font_family='Trebuchet MS', font_size = 12)
    chart.topbar.textbox('symbol', symbol_id)
    chart.topbar.textbox('Timeframe', '1D')
    chart.candle_style(up_color='#1a6a38', down_color='#aa1d1d',
                   border_up_color='#1a6a38', border_down_color='#aa1d1d',
                   wick_up_color='#1a6a38', wick_down_color='#aa1d1d')
    chart.volume_config(up_color='#1a6a38', down_color='#aa1d1d')

    chart.legend(visible = True, font_family = 'Trebuchet MS', ohlc = True, percent = True)

    # Columns: time | open | high | low | close | volume
    chart.set(df)
    chart.topbar.button('screenshot', 'Screenshot', func=take_screenshot)
    # use csv or client data for trades data
    response = int(input(f"What data do you want to use for trades data\n Options:\n 1. Client Data\n 2. Data from csv\n 3. Exit\n Response: "))
    if response in (1,2,3):
        if response == 1:
            try:
                trades = client.get_my_trades(symbol=symbol_id)
            except Exception as e:
                print(f'Failed to get data on historical trades for {symbol_id}. Error - {e}')
                sys.exit()
            trades = pd.DataFrame(trades)
            trades['time'] = pd.to_datetime(trades.time, unit='ms')
            trades = trades.sort_values('time') 

        elif response == 2:
            try:
                data_path = str(input("The File's name or path you want to read the data from: "))
                trades = pd.read_csv(data_path)
            except:
                print("Invalid file name, could not get data.")
                sys.exit()
        else:
            sys.exit()
    else:
        print("Invalid input. Input must be between 1 and 3.")

    for i in range(0, len(trades)):
        if trades['isBuyer'][i] == True:
            chart.marker(time = trades['time'][i], text = 'B', position = 'below', shape = 'arrow_up', color = '#1a6a38')
        else:
            chart.marker(time = trades['time'][i], text = 'S', position = 'above', shape = 'arrow_down', color = '#aa1d1d')

    chart.show(block=True)
    
def Weekly_Buy_Signal(weekly_df) -> bool:
    if weekly_df['MACD'][-1] > weekly_df['Signal_Line'][-1]:
        return True
    else: 
        return False
    
def Daily_Buy_Signal(daily_df) -> bool:
    if daily_df['MACD'][-1] > daily_df['Signal_Line'][-1]:
        return True
    else:
        return False
    
def Weekly_Sell_Signal(weekly_df) -> bool:
    if weekly_df['MACD'][-1] < weekly_df['Signal_Line'][-1]:
        return True
    else:
        return False
    
def Daily_Sell_Signal(daily_df) -> bool:
    if daily_df['MACD'][-1] < daily_df['Signal_Line'][-1]:
        return True
    else: 
        return False

def Cancel_limit_Orders(symbol_id:str) -> None: # cancel limit orders to get access of funds locked in limit order
    open_orders: list = client.get_open_orders()
    if len(open_orders) != 0:
        for i in range(0,len(open_orders)):
            if open_orders[i]['symbol'] == symbol_id:
                try:
                    client.cancel_order(symbol=symbol_id, orderId=open_orders[i]['orderId'])
                except Exception as e:
                    print(f'Failed to cancel limit order for {symbol_id}. Error - {e}')
            return None
    else: 
        return None

def Check_StopLoss(symbol_id: str, Stop_Loss: float) -> bool:
    ticker: dict = client.get_symbol_ticker(symbol=symbol_id)
    price: float = float(ticker['price'])
    # check if price of stop order is smaller than current price
    if price > Stop_Loss:
        return True
    else:
        return False

def Check_Position(symbol_id:str) -> bool:
    try:
        trades = client.get_my_trades(symbol=symbol_id)
    except Exception as e:
        print(f'Failed to get data on historical trades for {symbol_id}. Error - {e}')
        sys.exit()
    trades = pd.DataFrame(trades)
    trades['time'] = pd.to_datetime(trades.time, unit='ms')
    trades = trades.sort_values('time')
    print(trades)
    if trades['isBuyer'][len(trades)-1] == True:
        return True
    else:
        return False
    
def Strategy(Asset:str, Manual_SL:bool, Stop_Loss:float) -> None:
    In_position: bool = Check_Position(symbol_id=Asset)
    while not In_position:
        if calculate_investment(stable=stable, perc=perc) >= 10.00:
            weekly = get_weekly_data(asset=Asset, interval=week_interval, weeks=weeks)
            daily = get_daily_data(asset=Asset, interval=day_interval, day=days)
            # change conditions to exclude the Market sentiment function
            if (Weekly_Buy_Signal(weekly_df=weekly)) and (Daily_Buy_Signal(daily_df=daily)):    
                In_position = True

                time.sleep(1)
                Cancel_limit_Orders(symbol_id=Asset) # cancel all open limit orders for trading asset. Why? Cannot access funds, locked in limit order
                investment: float = calculate_investment(stable=stable, perc=perc)
                qty: float = quantitycalc(symbol_id=Asset, investment=investment)
                qty = math.trunc(qty * 10**5) / 10**5  # BTC trading quantities only allow 5 decimals
                # market buy order
                order = Market_Buy(asset=Asset, qty=qty)
                print(order)
                PriceBought: float = float(order['fills'][0]['price'])
                print(f'Quantity: {qty:.9f}')
                investment = float(order['cummulativeQuoteQty'])
                print(f"Bought: {investment:.2f} at {PriceBought:.2f}")
                Open_Time = pd.to_datetime(order['transactTime'], unit='ms') # time order filled
                Open_Time = str(Open_Time)
                print(f'Time: {Open_Time}')
                break # break infinite loop
            
            else:
                time.sleep(3600)

        else:
            balance = calculate_investment(stable=stable, perc=perc)
            print(f"Stable Coin Balance: {balance:.2f}")
            print('Minimum order amount for BTC is equal 10.00 USDT.')
            sys.exit()

    while In_position:
        # get value of position to exit loop if limit filled
        In_position: bool = Check_Position(symbol_id=Asset)

        weekly = get_weekly_data(asset=Asset, interval=week_interval, weeks=weeks)
        daily = get_daily_data(asset=Asset, interval=day_interval, day=days)

        if Daily_Sell_Signal(daily_df=daily) or Weekly_Sell_Signal(weekly_df=weekly):
            In_position = False

            Cancel_limit_Orders(symbol_id=Asset) # cancel all open limit orders for trading asset. Why? Cannot access funds, locked in limit order
            time.sleep(1)
            # check for qty availible of trading asset, after commision fees subtracted
            balance = client.get_asset_balance(asset=Asset[:-4]) # Return total balance for trading asset
            balance = float(balance['free']) # free balance of asset
            qty = math.trunc(balance * 10**5) / 10**5 # only allows upto 5 decimals in trading quantities
            # place market sell order
            order = Market_Sell(asset=Asset, qty=qty)
            print(order)
            SoldPrice: float = float(order['fills'][0]['price'])
            pricesold = float(order['cummulativeQuoteQty'])
            print(f"Sold: {pricesold:.2f} at {SoldPrice:.2f}")
            Close_Time = pd.to_datetime(order['transactTime'], unit='ms')
            print(f'Time: {Close_Time}')
            time.sleep(1)
            break

        elif Manual_SL:
            if Check_StopLoss(symbol_id=Asset, Stop_Loss=Stop_Loss):
                # cancel previous made Limit order to place new one
                # if change Stop_Limit order, rerun script to place new one at input price stored in "Stop_Loss parameter"
                # limit order can also be changed through binance app
                Cancel_limit_Orders(symbol_id=Asset)
                # place new limit order
                balance = client.get_asset_balance(asset=Asset[:-4]) # Return total balance for trading asset
                balance = float(balance['free']) # free balance of asset
                qty = math.trunc(balance * 10**5) / 10**5 # only allows upto 5 decimals in trading quantities
                # place limit sell order to act as stop loss
                order = client.order_limit_sell(
                    symbol=Asset,
                    quantity=qty,
                    price=f'{Stop_Loss}')
                # make "Manual_SL" equal to False to not place new stop loss order on next iteration of loop
                print(f"Stop_Limit order placed at {Stop_Loss}")
                Manual_SL = False
            else:
                print("Limit order not placed since the price attribute a invalid value.")

        else: 
            time.sleep(3600)
                
    In_position: bool = Check_Position(symbol_id=Asset)
    if not In_position:
        # calculate ROI
        # Check total PnL and investment information on dashboard application
        try:
            balance = client.get_asset_balance(asset=stable)
        except Exception as e:
            print(f'Failed to get balance for {stable}. Error - {e}')
        balance: float = float(balance['free'])

        try:
            ROI: float = balance - investment # current balance - investment
            if ROI > 0:
                print(f"Profit: {ROI:.2f}\n")
            else:
                print(f"Loss: {ROI:.2f}\n")
                time.sleep(1800)
        except Exception as e:
            sys.exit()
        # no need to write trades to csv, keep track with data from exchange
    
def main() -> None:
    start_time = time.time() # time of timer allways in sec 
    while True:
        current_time = time.time()
        elapsed_time = current_time - start_time
        Asset: str = coins[0]

        response = int(input("Do you wish to run the Algo trading strategy or display a chart showing your past trades: \n Options:\n 1. Run Strategy\n 2. Display chart\n 3. Exit\n Response: "))
        if response in (1,2,3):
            if response == 1:
                showChart = False
            elif response == 2:
                showChart = True
            else:
                sys.exit()

        daily = get_daily_data(asset=Asset, interval=day_interval, day=days)

        if showChart:
            weekly = get_weekly_data(asset=Asset, interval=week_interval, weeks=weeks)
            Visualize(symbol_id=Asset, df=daily) # visualize chart of strategy
            break
        else: 
            # Allow user to manually enter a stop loss
            Manual_SL: str = str(input("Do you want to add a stop loss to the strategy. Enter (y/n): "))
            if Manual_SL.lower() in ('y','n'):
                if Manual_SL.lower() == 'y':
                    Manual_SL: bool = True
                    SL : float = float(input('Manually enter stop loss to add to strategy: '))
                else:
                    Manual_SL: bool = False
                    SL : float = 0
                Strategy(Asset=Asset,Manual_SL=Manual_SL, Stop_Loss=SL)
            else:
                print("You entered an invalid value. Please enter either 'y' or 'n'.")

        if elapsed_time > timertime: # run timer and execute strategy until timer is reached endpoint 
            print(f"Finished trading in: {elapsed_time} seconds")  # prints if timer ended 
            break

if __name__ == "__main__":
    main()