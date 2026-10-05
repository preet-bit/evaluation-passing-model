import numpy as np
import pandas as pd
import time
import random
import itertools

def run_iq_capital_500_batch():
    print("==================================================================")
    print(" INITIATING 500-STRATEGY BATCH FOR IQ CAPITAL FUTURES CHALLENGE ")
    print(" Asset: S&P 500 (ES Daily) | Rules: <5% Max DD, >6% Target ")
    print("==================================================================")
    
    # 1. Load Data
    try:
        df = pd.read_csv('../data/ES_daily.csv', sep='\t', header=None)
        df.columns = ['date', 'open', 'high', 'low', 'close', 'volume']
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
    except Exception as e:
        print(f"Failed to load data: {e}")
        return
        
    print(f"Loaded {len(df)} days of historical S&P 500 Futures data.")
    
    # Pre-calculate common indicators for speed
    c = df['close'].values
    h = df['high'].values
    l = df['low'].values
    
    # True Range for Volatility-based Stop Loss
    tr1 = h[1:] - l[1:]
    tr2 = np.abs(h[1:] - c[:-1])
    tr3 = np.abs(l[1:] - c[:-1])
    tr = np.zeros(len(c))
    tr[1:] = np.maximum(tr1, np.maximum(tr2, tr3))
    
    # Generate exactly 500 Strategy Parameter Combinations
    print("Generating 500 Prop Firm Strategy Combinations...")
    # Parameters: (SMA Fast, SMA Slow, RSI Period, RSI Oversold, Stop Loss ATR Mult, Take Profit ATR Mult)
    sma_fasts = [5, 10, 20]
    sma_slows = [50, 100, 200]
    rsi_periods = [2, 4, 7]
    rsi_oversolds = [15, 20, 30]
    sl_atrs = [1.5, 2.0, 3.0]
    tp_atrs = [1.5, 2.0, 3.0, 4.0]
    
    all_combos = list(itertools.product(sma_fasts, sma_slows, rsi_periods, rsi_oversolds, sl_atrs, tp_atrs))
    random.seed(42)
    batch_500 = random.sample(all_combos, 500)
    
    # Prop Firm Rules
    START_CAPITAL = 50000
    MAX_DD_LIMIT = -0.05  # -5% Max Drawdown
    RISK_PER_TRADE = 0.005 # Risk 0.5% ($250) per trade
    
    passed_strategies = []
    
    print("Executing 500 Backtests simultaneously. Enforcing 5% Max Drawdown Circuit Breaker...")
    start_time = time.time()
    
    for idx, params in enumerate(batch_500):
        sma_f, sma_s, rsi_p, rsi_o, sl_atr, tp_atr = params
        
        # Calculate moving averages
        ma_fast = pd.Series(c).rolling(sma_f).mean().values
        ma_slow = pd.Series(c).rolling(sma_s).mean().values
        atr = pd.Series(tr).rolling(14).mean().values
        
        # Simple RSI (using pandas for speed over numpy loop)
        delta = pd.Series(c).diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=rsi_p).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_p).mean()
        rs = gain / (loss + 1e-9)
        rsi = 100 - (100 / (1 + rs))
        rsi = rsi.values
        
        # Vectorized Entry Signals
        # Buy if Short MA > Long MA (Uptrend) AND RSI < Oversold (Dip buying)
        entries = (ma_fast > ma_slow) & (rsi < rsi_o)
        
        capital = START_CAPITAL
        peak_capital = START_CAPITAL
        blown = False
        
        wins = 0
        losses = 0
        in_trade = False
        entry_price = 0
        stop_price = 0
        target_price = 0
        
        # To simulate realistically, we step through entries
        for i in range(max(sma_s, 14), len(c)):
            if blown:
                break
                
            if in_trade:
                # Check for SL or TP hits
                if l[i] <= stop_price:
                    capital -= (START_CAPITAL * RISK_PER_TRADE) # Lost 0.5%
                    losses += 1
                    in_trade = False
                elif h[i] >= target_price:
                    # Reward scaled by TP/SL ratio
                    reward = (START_CAPITAL * RISK_PER_TRADE) * (tp_atr / sl_atr)
                    capital += reward
                    wins += 1
                    in_trade = False
                    
                # Update peak and DD
                if capital > peak_capital:
                    peak_capital = capital
                drawdown = (capital - peak_capital) / peak_capital
                
                # IQ Capital 5% Max Drawdown Rule
                if drawdown <= MAX_DD_LIMIT:
                    blown = True
                    break
                    
            elif entries[i-1]: # Signal generated yesterday
                in_trade = True
                entry_price = c[i-1] # Enter at today's open (approximated as yesterday's close for simplicity)
                stop_price = entry_price - (atr[i-1] * sl_atr)
                target_price = entry_price + (atr[i-1] * tp_atr)
                
        total_trades = wins + losses
        if not blown and total_trades > 20:
            total_return = (capital - START_CAPITAL) / START_CAPITAL
            win_rate = wins / total_trades if total_trades > 0 else 0
            
            # Did it hit Prop Firm profit target? (IQ Capital requires usually 6% to pass)
            if total_return > 0.06:
                passed_strategies.append({
                    'params': params,
                    'return': total_return,
                    'win_rate': win_rate,
                    'trades': total_trades,
                    'final_balance': capital
                })

    elapsed = time.time() - start_time
    print(f"\nBatch processing complete in {elapsed:.2f} seconds.")
    print("==================================================================")
    print(f" TOTAL STRATEGIES TESTED: 500")
    print(f" STRATEGIES THAT PASSED IQ CAPITAL (0 Blowups, >6% Profit): {len(passed_strategies)}")
    print("==================================================================")
    
    if len(passed_strategies) > 0:
        # Sort by highest return
        passed_strategies.sort(key=lambda x: x['return'], reverse=True)
        print("TOP 3 PROP FIRM PASSING ALGORITHMS:")
        for i in range(min(3, len(passed_strategies))):
            strat = passed_strategies[i]
            p = strat['params']
            print(f"\nRank #{i+1}:")
            print(f"  Logic: {p[0]}-SMA > {p[1]}-SMA | RSI({p[2]}) < {p[3]}")
            print(f"  Risk: Stop Loss = {p[4]} ATR | Take Profit = {p[5]} ATR")
            print(f"  Metrics: {strat['win_rate']*100:.1f}% Win Rate | {strat['trades']} Trades")
            print(f"  Final Profit: +{strat['return']*100:.2f}% (Safe from 5% Drawdown)")
    else:
        print("NONE of the 500 strategies survived the strict 5% Drawdown limit.")

if __name__ == '__main__':
    run_iq_capital_500_batch()
