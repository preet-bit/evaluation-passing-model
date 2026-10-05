import asyncio
import json
import websockets
import time
from datetime import datetime

class LiveTripleConfirmationEngine:
    def __init__(self):
        self.symbol = "btcusdt"
        self.ws_url = f"wss://stream.binance.com:9443/ws/{self.symbol}@depth20@100ms"
        
        # Prop Firm Limits
        self.risk_usd = 200.0        
        self.reward_usd = 300.0      
        self.obi_threshold = 0.60    
        
        # Tracking States
        self.position = 0            
        self.entry_price = 0.0
        self.capital = 50000.0
        
        # New Structural States
        self.vpoc = 0.0
        self.vol_profile = {}
        self.cvd = 0.0
        self.price_history = []
        self.cvd_history = []

    def calculate_obi(self, bids, asks):
        bid_vol = sum(float(b[1]) for b in bids[:5])
        ask_vol = sum(float(a[1]) for a in asks[:5])
        total_vol = bid_vol + ask_vol
        if total_vol == 0: return 0
        return (bid_vol - ask_vol) / total_vol

    async def process_live_feed(self):
        print("==================================================================")
        print(" INITIATING LIVE TRIPLE-CONFIRMATION ENGINE (NO API KEY) ")
        print(" Tracking: VPOC | CVD Divergence | LOB Imbalance ")
        print("==================================================================")
        
        async with websockets.connect(self.ws_url) as ws:
            while True:
                try:
                    response = await ws.recv()
                    data = json.loads(response)
                    
                    bids = data.get('bids', [])
                    asks = data.get('asks', [])
                    if not bids or not asks: continue
                    
                    best_bid = float(bids[0][0])
                    best_ask = float(asks[0][0])
                    current_price = (best_bid + best_ask) / 2.0
                    obi = self.calculate_obi(bids, asks)
                    
                    # 1. Update Synthetic Volume Profile (VPOC)
                    tick_vol = float(bids[0][1]) + float(asks[0][1])
                    if current_price not in self.vol_profile:
                        self.vol_profile[current_price] = 0.0
                    self.vol_profile[current_price] += tick_vol
                    if self.vol_profile[current_price] > self.vol_profile.get(self.vpoc, 0):
                        self.vpoc = current_price
                        
                    # 2. Update CVD
                    if len(self.price_history) > 0:
                        if current_price > self.price_history[-1]: self.cvd += tick_vol
                        elif current_price < self.price_history[-1]: self.cvd -= tick_vol
                        
                    self.price_history.append(current_price)
                    self.cvd_history.append(self.cvd)
                    if len(self.price_history) > 50: # Short lookback for live fast demo
                        self.price_history.pop(0)
                        self.cvd_history.pop(0)
                    
                    # Print Live Tape
                    if int(time.time()) % 2 == 0 and time.time() - getattr(self, 'last_log_time', 0) > 1:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] Price: {current_price:.2f} | VPOC: {self.vpoc:.2f} | CVD: {self.cvd:+.0f} | OBI Skew: {obi*100:+.1f}%")
                        self.last_log_time = time.time()

                    # EXECUTION LOGIC (Triple Confirmation)
                    if self.position == 0 and len(self.price_history) == 50:
                        recent_low = min(self.price_history)
                        recent_high = max(self.price_history)
                        cvd_slope = self.cvd_history[-1] - self.cvd_history[0]
                        
                        # LONG: At VPOC, CVD Exhausted, Bid Absorption
                        if current_price <= self.vpoc and cvd_slope > 0 and obi > self.obi_threshold:
                            self.position = 1
                            self.entry_price = best_ask 
                            print(f">>> [LIVE TRADE] Executed LONG at {self.entry_price:.2f}")
                            print(f"    CONFIRM 1: Price at VPOC ({self.vpoc:.2f})")
                            print(f"    CONFIRM 2: CVD Exhaustion Slope (+{cvd_slope:.0f})")
                            print(f"    CONFIRM 3: Passive Limit Absorption (OBI {obi*100:+.1f}%)")
                            
                        # SHORT: At VPOC, CVD Exhausted, Ask Resistance
                        elif current_price >= self.vpoc and cvd_slope < 0 and obi < -self.obi_threshold:
                            self.position = -1
                            self.entry_price = best_bid
                            print(f">>> [LIVE TRADE] Executed SHORT at {self.entry_price:.2f}")
                            print(f"    CONFIRM 1: Price at VPOC ({self.vpoc:.2f})")
                            print(f"    CONFIRM 2: CVD Exhaustion Slope ({cvd_slope:.0f})")
                            print(f"    CONFIRM 3: Passive Ask Resistance (OBI {obi*100:+.1f}%)")
                            
                    elif self.position != 0:
                        pnl = (current_price - self.entry_price) if self.position == 1 else (self.entry_price - current_price)
                        if pnl <= -self.risk_usd:
                            self.capital -= self.risk_usd
                            print(f"    [EXIT] STOP LOSS. Balance: ${self.capital:.2f}")
                            self.position = 0
                            await asyncio.sleep(5) 
                        elif pnl >= self.reward_usd:
                            self.capital += self.reward_usd
                            print(f"    [EXIT] TAKE PROFIT. Balance: ${self.capital:.2f}")
                            self.position = 0
                            await asyncio.sleep(5)
                            
                except Exception as e:
                    await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(LiveTripleConfirmationEngine().process_live_feed())
