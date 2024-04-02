import os
from binance.client import Client
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sn

bridge = 'USDT'
startcoin = 'TRX'
size_of_list = 18
api_key = "2q3NlYGs9oVSs0I1szP7UHMwd9YaEM8lj6xp2fb1E37GoIU0TDoIibKndRH46D1Q"
api_secret = "np7OW0y7uaMmr9O372v1mGevgBNi4w4jG6kRbsmCuNEbGkJ3a1EoS9oActkygrVk"
client = Client(api_key, api_secret)


def get_ticker_price(ticker_symbol: str, days: int, granularity: str):
    """
    Gets ticker price of a specific coin
    """

    target_date = (datetime.now() - timedelta(days=days)).strftime("%d %b %Y %H:%M:%S")
    key = f"{ticker_symbol}"
    end_date = datetime.now()
    end_date = end_date.strftime("%d %b %Y %H:%M:%S")

    coindata = pd.DataFrame(columns=[key])

    prices = []
    dates = []
    for result in client.get_historical_klines(
            ticker_symbol, granularity, target_date, end_date, limit=1000
    ):
        date = datetime.utcfromtimestamp(result[0] / 1000).strftime("%d %b %Y %H:%M:%S")
        price = float(result[1])
        dates.append(date)
        prices.append(price)

    coindata[key] = prices
    coindata['date'] = dates

    return (coindata.reindex(columns=['date', key]))


def get_price_data(tickers, days=1, granularity="1m"):
    '''
    Collects price data from the binance server.
    '''
    failures = []
    coindata = get_ticker_price(tickers[0], days, granularity)
    for tick in tickers[1:]:
        newdata = get_ticker_price(tick, days, granularity)
        if not newdata.empty:
            coindata = coindata.merge(newdata, how='left')

        else:
            failures.append(tick)
    print('The following coins do not have historical data')
    print(failures)
    return (coindata)


def take_rolling_average(coindata):
    RA = pd.DataFrame()

    for column in coindata:
        if column != 'date':
            RA[column] = coindata[column].rolling(window=3).mean()
    return (RA)


def pick_coins(start_ticker, day_corr, week_corr, two_week_corr, n):
    '''
    Takes your starting coin, then sequentially picks the coin that jointly maximises
    the correlation for the whole coin list.

    INPUT:
    start_ticker : STR : The ticker for a coin you wish to include in your list
    day_corr     : PD.CORR : daily correlation data
    week_corr    : PD.CORR : Weekly correlation data
    two_week_corr: PD.CORR : bi-weekly correlation data
    n            : INTEGER : number of coins to include in your list.
    '''

    coinlist = [start_ticker]
    for i in range(n - 1):
        new_day_corr = day_corr[~day_corr.index.isin(coinlist)]
        new_week_corr = week_corr[~week_corr.index.isin(coinlist)]
        new_two_week_corr = two_week_corr[~two_week_corr.index.isin(coinlist)]
        corrsum = pd.DataFrame()
        for coin in coinlist:
            if corrsum.empty:
                corrsum = new_day_corr[coin] + new_week_corr[coin] + new_two_week_corr[coin]
            else:
                corrsum += new_day_corr[coin] + new_week_corr[coin] + new_two_week_corr[coin]

        ind = corrsum.argmax()
        coinlist.append(new_day_corr.index[ind])
    return (coinlist)


if __name__ == '__main__':
    print("Starting: Bridge: " + bridge, "Startcoin: " + startcoin, "Size of list: " + str(size_of_list))
    # Download ALL the coinpairs from binance
    exchange_info = client.get_exchange_info()

    full_coin_list = []

    # Only keep the pairs to our bridge coin
    for s in exchange_info['symbols']:
        if s['symbol'].endswith(bridge):
            full_coin_list.append(s['symbol'][:-len(bridge)])

    # List of words to eliminate futures markets coins
    forbidden_words = ['DOWN', 'UP', 'BULL', 'BEAR']
    for forbidden in forbidden_words:
        full_coin_list = [word for word in full_coin_list if forbidden not in word]

    # Alphabetical order because pretty :)
    full_coin_list.sort()

    # Collect the data for 3 different windows (1 day, 1 week, 2 weeks)
    # with granularity (1 minute, 1 hour ,2 hours)

    cointickers = [coin + bridge for coin in full_coin_list]
    print(cointickers)
    day_data = get_price_data(cointickers, 1, "1m")
    week_data = get_price_data(cointickers, 7, "1h")
    two_week_data = get_price_data(cointickers, 14, "2h")

    ## Collect the percentage change for correlation measurements

    day_data = day_data[day_data.columns.difference(['date'])].pct_change()
    week_data = week_data[week_data.columns.difference(['date'])].pct_change()
    two_week_data = two_week_data[two_week_data.columns.difference(['date'])].pct_change()

    # Calculate the rolling average (RA3) for all the coins

    RA_day_data = take_rolling_average(day_data)
    RA_week_data = take_rolling_average(week_data)
    RA_2week_data = take_rolling_average(two_week_data)

    # take the correlations of the rolling averages.

    day_corr = RA_day_data.corr()
    week_corr = RA_week_data.corr()
    two_week_corr = RA_2week_data.corr()

    coinlist = pick_coins(startcoin + bridge, day_corr, week_corr, two_week_corr, size_of_list)

    # calculate stds
    scaled_day_data = (day_data / day_data.max())
    scaled_week_data = (week_data / week_data.max())
    scaled_two_week_data = (two_week_data / two_week_data.max())

    day_std = scaled_day_data.std()
    week_std = scaled_week_data.std()
    two_week_std = scaled_two_week_data.std()

    maxjumpday = day_data.max() - day_data.min()
    maxjumptwoweek = two_week_data.max() - two_week_data.min()
    maxjumptwoweek[coinlist].hist(label='two_week')
    maxjumpday[coinlist].hist(label='day')
    plt.title('maximum jump-size, a measure of volatility')
    plt.legend()
    print('Top 10 daily maximum jumps')
    print(maxjumpday[coinlist].sort_values(ascending=False)[-8:])
    print('Top 10 two weekly maximum jumps')
    print(maxjumptwoweek[coinlist].sort_values(ascending=False)[-8:])

    coins = [coin.replace(bridge, '') for coin in coinlist]
    print("Coins: " + str(len(coins)))
    for coin in coins:
        print(coin)

    volumedata = client.get_ticker()

    for data in volumedata:
        if data['symbol'] in coinlist:
            usdtradevol = float(data['volume']) * float(data['weightedAvgPrice'])
            print(data['symbol'], ' 24hr trade volume is ', usdtradevol, bridge)
            if usdtradevol < 3000000:
                print('Warning, low trade volumes can increase the probability of slippage')
                coins.remove(data['symbol'][0:-len(bridge)])

    print("Coins with low trade volume removed: " + str(len(coins)))

    for coin in coins:
        print(coin)
