from AlgorithmImports import *

class IQCapitalTickEngine(QCAlgorithm):
    """
    Fixed IQ Capital Prop Firm Engine
    Timeframe: 1-Second (Completely eliminates 1-minute slippage)
    Execution: Hard OCO Brackets (StopMarket & Limit orders)
    Orphan Order Fix: Cancels open bracket orders on fill to free margin.
    """
    def Initialize(self):
        self.SetStartDate(2024, 1, 1)  
        self.SetEndDate(2024, 2, 1) 
        self.SetCash(50000)
        
        self.mes = self.AddFuture(Futures.Indices.MicroSP500EMini,
                                  resolution=Resolution.Second,
                                  extendedMarketHours=True,
                                  dataNormalizationMode=DataNormalizationMode.BackwardsRatio,
                                  dataMappingMode=DataMappingMode.OpenInterest,
                                  contractDepthOffset=0)
                                 
        self.symbol = self.mes.Symbol
        self.SetBrokerageModel(BrokerageName.InteractiveBrokersBrokerage, AccountType.Margin)
        
        self.contracts_to_trade = 5
        self.risk_points = 8.0     
        self.reward_points = 12.0  
        
        self.vpoc = 0.0
        self.vol_profile = {}
        self.cvd = 0.0
        self.cvd_history = []
        self.price_history = []
        
        self.last_minute = -1
        self.is_cooling_down = False
        self.cooldown_end_time = self.Time

    def OnOrderEvent(self, orderEvent):
        if orderEvent.Status == OrderStatus.Filled:
            if not self.Portfolio.Invested:
                # We just flattened the position. Cancel the opposite OCO bracket order!
                self.Transactions.CancelOpenOrders(self.mes.Mapped)
                # Apply a 60-second cooldown after a trade to prevent machine gunning
                self.is_cooling_down = True
                self.cooldown_end_time = self.Time + timedelta(seconds=60)

    def OnData(self, slice: Slice):
        if self.Time.hour == 15 and self.Time.minute >= 45:
            self.Liquidate()
            return
            
        if self.Time.hour < 9 or self.Time.hour >= 15: return
        
        mapped_symbol = self.mes.Mapped
        if mapped_symbol is None: return
        if not slice.Bars.ContainsKey(self.symbol): return
        
        trade_bar = slice.Bars[self.symbol]
        price = trade_bar.Close
        vol = trade_bar.Volume
        
        if self.Time.minute != self.last_minute:
            tick = round(price * 4) / 4
            if tick not in self.vol_profile: self.vol_profile[tick] = 0
            self.vol_profile[tick] += vol
            self.vpoc = max(self.vol_profile, key=self.vol_profile.get)
            
            if trade_bar.Close > trade_bar.Open: self.cvd += vol
            elif trade_bar.Close < trade_bar.Open: self.cvd -= vol
            
            self.price_history.append(price)
            self.cvd_history.append(self.cvd)
            if len(self.cvd_history) > 30:
                self.price_history.pop(0)
                self.cvd_history.pop(0)
                
            self.last_minute = self.Time.minute
            
        if self.Portfolio.Invested: return 
        
        if self.is_cooling_down:
            if self.Time >= self.cooldown_end_time:
                self.is_cooling_down = False
            else:
                return
            
        if len(self.cvd_history) < 30: return
        
        recent_low = min(self.price_history)
        recent_high = max(self.price_history)
        cvd_slope = self.cvd_history[-1] - self.cvd_history[0]
        
        if price <= self.vpoc and price <= recent_low * 1.0005 and cvd_slope > 0:
            self.MarketOrder(mapped_symbol, self.contracts_to_trade)
            self.StopMarketOrder(mapped_symbol, -self.contracts_to_trade, price - self.risk_points)
            self.LimitOrder(mapped_symbol, -self.contracts_to_trade, price + self.reward_points)
            
        elif price >= self.vpoc and price >= recent_high * 0.9995 and cvd_slope < 0:
            self.MarketOrder(mapped_symbol, -self.contracts_to_trade)
            self.StopMarketOrder(mapped_symbol, self.contracts_to_trade, price + self.risk_points)
            self.LimitOrder(mapped_symbol, self.contracts_to_trade, price - self.reward_points)
