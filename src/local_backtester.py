import yfinance as yf
import pandas as pd
import numpy as np

def run_fast_velocity_backtest():
    print("==================================================================")
    print(" INITIATING HIGH-VELOCITY BACKTEST (1-MINUTE INTRADAY ES) ")
    print(" Goal: Hit $3,000 Profit within a strict 20-Day Limit ")
    print("==================================================================")
    
    print("Downloading last 7 Days of ultra-fast 1-Minute Data...")
    df = yf.download("ES=F", interval="1m", period="7d", progress=False)
    
    if df.empty:
        print("Error: Could not fetch data.")
        return
        
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.loc[:,~df.columns.duplicated()]
        
    print(f"Data downloaded: {len(df)} 1-minute intraday bars.")
    
    # Pre-calculate CVD
    df['Delta'] = np.where(df['Close'] > df['Open'], df['Volume'], -df['Volume'])
    df['CVD'] = df['Delta'].cumsum()
    
    capital = 50000.0
    risk_usd = 200.0
    reward_usd = 300.0
    position = 0
    entry_price = 0.0
    trades = 0
    wins = 0
    
    price_levels = {}
    vpoc = float(df['Close'].iloc[0])
    cvd_lookback = 30 # 30 minutes
    
    for i in range(cvd_lookback, len(df)):
        current_price = float(df['Close'].iloc[i])
        vol = float(df['Volume'].iloc[i])
        
        tick = round(current_price * 4) / 4
        price_levels[tick] = price_levels.get(tick, 0) + vol
        if price_levels[tick] > price_levels.get(vpoc, 0):
            vpoc = tick
            
        if position == 0:
            dt = df.index[i]
            if not (9 <= dt.hour <= 15): continue # Expanded trading window for higher frequency
            
            recent_prices = df['Close'].iloc[i-cvd_lookback : i]
            recent_cvd = df['CVD'].iloc[i-cvd_lookback : i]
            
            recent_low = float(recent_prices.min())
            recent_high = float(recent_prices.max())
            cvd_slope = float(recent_cvd.iloc[-1]) - float(recent_cvd.iloc[0])
            
            if current_price <= vpoc and current_price <= recent_low * 1.0005 and cvd_slope > 0:
                position = 1
                entry_price = current_price
                trades += 1
                
            elif current_price >= vpoc and current_price >= recent_high * 0.9995 and cvd_slope < 0:
                position = -1
                entry_price = current_price
                trades += 1
                
        else:
            pnl_points = (current_price - entry_price) if position == 1 else (entry_price - current_price)
            pnl_usd = pnl_points * 50
            
            if pnl_usd <= -risk_usd:
                capital -= risk_usd
                position = 0
            elif pnl_usd >= reward_usd:
                capital += reward_usd
                wins += 1
                position = 0
                
            dt = df.index[i]
            if dt.hour == 15 and dt.minute >= 45:
                capital += pnl_usd
                if pnl_usd > 0: wins += 1
                position = 0

    print("\n==================================================================")
    print(" 7-DAY ACCELERATED BACKTEST COMPLETE ")
    print("==================================================================")
    if trades > 0:
        win_rate = (wins / trades) * 100
        print(f"Total Trades in 7 Days: {trades}")
        print(f"Win Rate:               {win_rate:.1f}%")
        
        profit = capital - 50000
        print(f"Gross Profit (7 Days):  +${profit:.2f}")
        
        # Project out to 20 days
        projected_20_days = profit * (20 / 7)
        print(f"Projected 20-Day PnL:   +${projected_20_days:.2f}")
    print("==================================================================")

if __name__ == '__main__':
    run_fast_velocity_backtest()
