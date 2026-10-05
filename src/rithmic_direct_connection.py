import asyncio
import os
from async_rithmic import RithmicClient, TimeBarType, OrderPlacement, OrderType

async def main():
    print("==================================================================")
    print(" INITIATING RITHMIC WEBSOCKET CONNECTION ")
    print(" Engine: Python -> Rithmic Paper Trading ")
    print("==================================================================")

    # 1. YOUR RITHMIC CREDENTIALS (AMP Futures Demo)
    USER = "preetlio271@gmail.com"
    PASSWORD = "F-apQ5LC?jQU37G"
    
    # 2. RITHMIC CONNECTION SETTINGS
    SYSTEM_NAME = "Rithmic Paper Trading"
    APP_NAME = "Python_Algo_Engine"
    APP_VERSION = "1.0.0"
    URL = "rituz00100.rithmic.com:443" # Standard Rithmic Test/Paper URL

    print("Connecting to Rithmic Servers...")
    try:
        # Initialize the client
        client = RithmicClient(
            user=USER, 
            password=PASSWORD, 
            system_name=SYSTEM_NAME, 
            app_name=APP_NAME, 
            app_version=APP_VERSION, 
            url=URL
        )
        
        await client.connect()
        print(">>> SUCCESSFULLY CONNECTED TO RITHMIC!")
        
        # NOTE: Once connected, this is where the VPOC + CVD Engine hooks into 
        # the client's Market Data subscription (client.subscribe_market_data)
        # and executes via client.submit_order()
        
        print("\nWaiting for market data stream...")
        # Keep the connection alive
        await asyncio.sleep(3600)

    except Exception as e:
        print(f"FAILED TO CONNECT: {e}")
        print("Please check your Username, Password, and System Name.")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
