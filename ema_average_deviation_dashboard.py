import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# Complete list of Nifty 200 stocks
nifty_200_stocks = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "HINDUNILVR.NS",
    "ICICIBANK.NS", "KOTAKBANK.NS", "SBIN.NS", "BAJFINANCE.NS", "BHARTIARTL.NS","ITC.NS"
    # ... (add the rest of the stocks here)
]

# Function to fetch and process stock data
def fetch_stock_data(ticker):
    start_date = '2018-01-01'
    end_date = datetime.now().strftime('%Y-%m-%d')
    stock_data = yf.download(ticker, start=start_date, end=end_date)
    
    if stock_data.empty:
        return stock_data

    if stock_data.index[-1] < pd.to_datetime(end_date):
        last_few_days = yf.download(ticker, start=(datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d'), end=end_date)
        stock_data = stock_data.combine_first(last_few_days)
    
    stock_data['EMA200'] = stock_data['Close'].ewm(span=200, adjust=False).mean()
    stock_data['Deviation'] = stock_data['Close'] - stock_data['EMA200']
    
    return stock_data

# Function to add deviation lines to the stock data
def add_deviation_lines(stock_data):
    max_deviations = []
    current_deviation = None
    deviation_points = []

    for i in range(1, len(stock_data)):
        if stock_data['Deviation'].iloc[i] < 0:
            if current_deviation is None or stock_data['Deviation'].iloc[i] < current_deviation:
                current_deviation = stock_data['Deviation'].iloc[i]
                deviation_point = stock_data.index[i]
        elif stock_data['Deviation'].iloc[i] >= 0 and current_deviation is not None:
            max_deviations.append(current_deviation)
            deviation_points.append(deviation_point)
            current_deviation = None

    if current_deviation is not None:
        max_deviations.append(current_deviation)
        deviation_points.append(deviation_point)

    average_deviation = np.mean(max_deviations)
    stock_data['AvgDeviationLine'] = stock_data['EMA200'] + average_deviation

    below_avg_deviation_points = []
    max_deviations_below_avg = []
    current_below_avg_deviation = None

    for i in range(1, len(stock_data)):
        if stock_data['Close'].iloc[i] < stock_data['AvgDeviationLine'].iloc[i]:
            deviation_below_avg = stock_data['Close'].iloc[i] - stock_data['AvgDeviationLine'].iloc[i]
            if current_below_avg_deviation is None or deviation_below_avg < current_below_avg_deviation:
                current_below_avg_deviation = deviation_below_avg
                below_avg_deviation_point = stock_data.index[i]
        elif stock_data['Close'].iloc[i] >= stock_data['AvgDeviationLine'].iloc[i] and current_below_avg_deviation is not None:
            max_deviations_below_avg.append(current_below_avg_deviation)
            below_avg_deviation_points.append(below_avg_deviation_point)
            current_below_avg_deviation = None

    if current_below_avg_deviation is not None:
        max_deviations_below_avg.append(current_below_avg_deviation)
        below_avg_deviation_points.append(below_avg_deviation_point)

    average_below_avg_deviation = np.mean(max_deviations_below_avg)
    stock_data['AvgBelowAvgDeviationLine'] = stock_data['AvgDeviationLine'] + average_below_avg_deviation

    stock_data['PercentDiffAvgDevLine_AvgBelowAvgDevLine'] = ((stock_data['AvgBelowAvgDeviationLine'] - stock_data['AvgDeviationLine']) / stock_data['AvgDeviationLine']) * 100
    stock_data['PercentDiffEMA_AvgDevLine'] = ((stock_data['AvgDeviationLine'] - stock_data['EMA200']) / stock_data['EMA200']) * 100

    return deviation_points, below_avg_deviation_points, max_deviations_below_avg, stock_data

# Function to check if a stock meets the condition
def check_condition(stock_data):
    if stock_data.empty:
        return False
    
    last_close = stock_data['Close'].iloc[-1]
    last_ema200 = stock_data['EMA200'].iloc[-1]
    last_avg_deviation_line = stock_data['AvgDeviationLine'].iloc[-1]
    
    return last_close < last_ema200 and last_close > last_avg_deviation_line

# Function to plot stock data
def plot_stock_data(stock_data, ticker, avg_max_deviation_below_avg, avg_max_deviation_below_avg_dev):
    deviation_points, below_avg_deviation_points, max_deviations_below_avg, stock_data = add_deviation_lines(stock_data)

    ema200_points = stock_data[stock_data['Close'] <= stock_data['EMA200']].index
    avg_deviation_points = stock_data[stock_data['Close'] <= stock_data['AvgDeviationLine']].index
    max_deviation_points = stock_data[stock_data['Close'] <= stock_data['AvgBelowAvgDeviationLine']].index

    plt.figure(figsize=(14, 7))
    plt.plot(stock_data['Close'], label=f'{ticker} Stock Price')
    plt.plot(stock_data['EMA200'], label='200-day EMA', color='orange')
    plt.scatter(deviation_points, stock_data.loc[deviation_points, 'Close'], color='red', label='Max Deviation Points')
    plt.plot(stock_data['AvgDeviationLine'], label='Average Deviation Line Below EMA', linestyle='--', color='green')
    plt.plot(stock_data['AvgBelowAvgDeviationLine'], label='Avg Max Deviation Below Avg Line', linestyle='--', color='purple')
    plt.scatter(below_avg_deviation_points, stock_data.loc[below_avg_deviation_points, 'Close'], color='blue', label='Deviation Below Avg Line')

    plt.scatter(ema200_points, stock_data.loc[ema200_points, 'Close'], color='green', label='Below EMA 200')
    plt.scatter(avg_deviation_points, stock_data.loc[avg_deviation_points, 'Close'], color='blue', label='Below Avg Deviation Line')
    plt.scatter(max_deviation_points, stock_data.loc[max_deviation_points, 'Close'], color='red', label='Below Max Deviation Line')

    # Add unusual deviations to the plot
    plt.plot(stock_data['AvgDeviationLine'] - avg_max_deviation_below_avg_dev, linestyle='--', color='pink', label='Unusual Deviation from Avg Deviation Line')
    plt.plot(stock_data['AvgBelowAvgDeviationLine'] - avg_max_deviation_below_avg, linestyle='--', color='cyan', label='Unusual Deviation from Avg Max Deviation Below Avg Line')

    plt.title(f'{ticker} Stock Price with 200-day EMA and Deviation Points')
    plt.xlabel('Date')
    plt.ylabel('Price')
    plt.legend()
    plt.grid(True)
    st.pyplot(plt)

# Streamlit app
st.title('NSE Stock Analysis Dashboard')

# Dropdown menu for selecting an NSE ticker
ticker = st.selectbox('Select NSE ticker symbol:', nifty_200_stocks)

if ticker:
    stock_data = fetch_stock_data(ticker)
    if not stock_data.empty:
        deviation_points, below_avg_deviation_points, max_deviations_below_avg, stock_data = add_deviation_lines(stock_data)
        st.write("## Stock Data Summary")
        latest_close = stock_data['Close'].iloc[-1]
        latest_ema200 = stock_data['EMA200'].iloc[-1]
        avg_deviation_line = stock_data['AvgDeviationLine'].iloc[-1]
        avg_below_avg_deviation_line = stock_data['AvgBelowAvgDeviationLine'].iloc[-1]
        
        st.write(f"**Latest Date:** {stock_data.index[-1].strftime('%Y-%m-%d')}")
        st.write(f"**Latest Closing Price:** {latest_close:.2f}")
        st.write(f"**Latest EMA 200 Price:** {latest_ema200:.2f}")
        st.write(f"**Difference Between Latest Closing Price and EMA 200:** {latest_close - latest_ema200:.2f} ({((latest_close - latest_ema200) / latest_ema200) * 100:.2f}%)")
        st.write(f"**Average Deviation Line Price:** {avg_deviation_line:.2f} ({((avg_deviation_line - latest_ema200) / latest_ema200) * 100:.2f}%)")
        st.write(f"**Avg Max Deviation Below Avg Line Price:** {avg_below_avg_deviation_line:.2f} ({((avg_below_avg_deviation_line - latest_ema200) / latest_ema200) * 100:.2f}%)")
        st.write(f"**Difference Between EMA 200 and Average Deviation Line:** {latest_ema200 - avg_deviation_line:.2f} ({((latest_ema200 - avg_deviation_line) / latest_ema200) * 100:.2f}%)")
        st.write(f"**Difference Between Average Deviation Line and Avg Max Deviation Below Avg Line:** {avg_below_avg_deviation_line - avg_deviation_line:.2f} ({((avg_below_avg_deviation_line - avg_deviation_line) / avg_deviation_line) * 100:.2f}%)")

        # Calculate avg_max_deviation_below_avg
        max_deviation_below_avg_periods = []
        current_max_deviation_below_avg = None
        for i in range(1, len(stock_data)):
            if stock_data['Close'].iloc[i] < stock_data['AvgBelowAvgDeviationLine'].iloc[i]:
                deviation_below_avg = stock_data['Close'].iloc[i] - stock_data['AvgBelowAvgDeviationLine'].iloc[i]
                if current_max_deviation_below_avg is None or deviation_below_avg < current_max_deviation_below_avg:
                    current_max_deviation_below_avg = deviation_below_avg
                    max_deviation_point_below_avg = stock_data.index[i]
            elif stock_data['Close'].iloc[i] >= stock_data['AvgBelowAvgDeviationLine'].iloc[i] and current_max_deviation_below_avg is not None:
                max_deviation_below_avg_periods.append((max_deviation_point_below_avg, current_max_deviation_below_avg))
                current_max_deviation_below_avg = None

        if current_max_deviation_below_avg is not None:
            max_deviation_below_avg_periods.append((max_deviation_point_below_avg, current_max_deviation_below_avg))

        avg_max_deviation_below_avg = np.mean([deviation for _, deviation in max_deviation_below_avg_periods])

        # Highlight dates where the deviation price points are less than the max deviation price points
        highlighted_dates = []
        non_highlighted_deviations = []
        for point, deviation in max_deviation_below_avg_periods:
            if deviation < avg_max_deviation_below_avg:
                highlighted_dates.append((point, deviation, stock_data.loc[point, 'Close'], (deviation / stock_data.loc[point, 'AvgBelowAvgDeviationLine']) * 100))
            else:
                non_highlighted_deviations.append(deviation)

        if highlighted_dates:
            st.write("## Highlighted Dates (Below Avg Max Deviation Below Avg Line)")
            for date, deviation, close, percent_change in highlighted_dates:
                st.markdown(f"<span style='background-color: yellow'>Date: {date.strftime('%Y-%m-%d')}, Price: {close:.2f}, Deviation: {deviation:.2f}, Percent Change: {percent_change:.2f}%</span>", unsafe_allow_html=True)

        avg_max_deviation_below_avg_excluding_highlighted = np.mean(non_highlighted_deviations)
        st.write(f"**Average of Maximum Deviation Price Points Below Avg Max Deviation Below Avg Line (Including Highlighted):** {avg_max_deviation_below_avg:.2f}")
        st.write(f"**Average of Maximum Deviation Price Points Below Avg Max Deviation Below Avg Line (Excluding Highlighted):** {avg_max_deviation_below_avg_excluding_highlighted:.2f}")

        # Calculate avg_max_deviation_below_avg_dev
        max_deviation_below_avg_dev_periods = []
        current_max_deviation_below_avg_dev = None
        for i in range(1, len(stock_data)):
            if stock_data['Close'].iloc[i] < stock_data['AvgDeviationLine'].iloc[i]:
                deviation_below_avg_dev = stock_data['Close'].iloc[i] - stock_data['AvgDeviationLine'].iloc[i]
                if current_max_deviation_below_avg_dev is None or deviation_below_avg_dev < current_max_deviation_below_avg_dev:
                    current_max_deviation_below_avg_dev = deviation_below_avg_dev
                    max_deviation_point_below_avg_dev = stock_data.index[i]
            elif stock_data['Close'].iloc[i] >= stock_data['AvgDeviationLine'].iloc[i] and current_max_deviation_below_avg_dev is not None:
                max_deviation_below_avg_dev_periods.append((max_deviation_point_below_avg_dev, current_max_deviation_below_avg_dev))
                current_max_deviation_below_avg_dev = None

        if current_max_deviation_below_avg_dev is not None:
            max_deviation_below_avg_dev_periods.append((max_deviation_point_below_avg_dev, current_max_deviation_below_avg_dev))

        avg_max_deviation_below_avg_dev = np.mean([deviation for _, deviation in max_deviation_below_avg_dev_periods])

        # Highlight dates where the deviation price points are less than the avg max deviation price points
        highlighted_avg_dev_dates = []
        non_highlighted_avg_dev_deviations = []
        for point, deviation in max_deviation_below_avg_dev_periods:
            if deviation < avg_max_deviation_below_avg_dev:
                highlighted_avg_dev_dates.append((point, deviation, stock_data.loc[point, 'Close'], (deviation / stock_data.loc[point, 'AvgDeviationLine']) * 100))
            else:
                non_highlighted_avg_dev_deviations.append(deviation)

        if highlighted_avg_dev_dates:
            st.write("## Highlighted Dates (Below Avg Deviation Line)")
            for date, deviation, close, percent_change in highlighted_avg_dev_dates:
                st.markdown(f"<span style='background-color: yellow'>Date: {date.strftime('%Y-%m-%d')}, Price: {close:.2f}, Deviation: {deviation:.2f}, Percent Change: {percent_change:.2f}%</span>", unsafe_allow_html=True)

        avg_max_deviation_below_avg_dev_excluding_highlighted = np.mean(non_highlighted_avg_dev_deviations)
        st.write(f"**Average of Maximum Deviation Price Points Below Avg Deviation Line (Including Highlighted):** {avg_max_deviation_below_avg_dev:.2f}")
        st.write(f"**Average of Maximum Deviation Price Points Below Avg Deviation Line (Excluding Highlighted):** {avg_max_deviation_below_avg_dev_excluding_highlighted:.2f}")

        # List of deviation points below avg deviation line
        st.write("## Deviation Points Below Avg Deviation Line")
        for point, deviation in max_deviation_below_avg_dev_periods:
            percent_change = (deviation / stock_data.loc[point, 'AvgDeviationLine']) * 100
            st.write(f"Date: {point.strftime('%Y-%m-%d')}, Price: {stock_data.loc[point, 'Close']:.2f}, Deviation: {deviation:.2f}, Percent Change: {percent_change:.2f}%")

        # List of deviation points below avg max deviation below avg line
        st.write("## Deviation Points Below Avg Max Deviation Below Avg Line")
        for point, deviation in max_deviation_below_avg_periods:
            percent_change = (deviation / stock_data.loc[point, 'AvgBelowAvgDeviationLine']) * 100
            st.write(f"Date: {point.strftime('%Y-%m-%d')}, Price: {stock_data.loc[point, 'Close']:.2f}, Deviation: {deviation:.2f}, Percent Change: {percent_change:.2f}%")

        # Institution level of entry
        entry_range_start = avg_deviation_line
        entry_range_end_including = avg_below_avg_deviation_line + avg_max_deviation_below_avg
        entry_range_end_excluding = avg_below_avg_deviation_line + avg_max_deviation_below_avg_excluding_highlighted
        st.write(f"**Institution Level of Entry (Including Highlighted):** The price range for entry would be between {entry_range_start:.2f} and {entry_range_end_including:.2f}")
        st.write(f"**Institution Level of Entry (Excluding Highlighted):** The price range for entry would be between {entry_range_start:.2f} and {entry_range_end_excluding:.2f}")

        plot_stock_data(stock_data, ticker, avg_max_deviation_below_avg, avg_max_deviation_below_avg_dev)
    else:
        st.write(f"No data found for {ticker}")

# Screening section
st.header('Screening')
if st.button('Run Screener'):
    screened_stocks = []
    for stock in nifty_200_stocks:
        stock_data = fetch_stock_data(stock)
        if not stock_data.empty:
            # Ensure deviation lines are added before checking condition
            deviation_points, below_avg_deviation_points, max_deviations_below_avg, stock_data = add_deviation_lines(stock_data)
            if check_condition(stock_data):
                screened_stocks.append(stock)
    st.write('Stocks meeting the condition (price below EMA 200 and above average deviation line):')
    st.write(screened_stocks)
