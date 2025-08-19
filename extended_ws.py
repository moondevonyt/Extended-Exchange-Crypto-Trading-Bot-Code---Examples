import os
import json
import time
import websocket
import threading
from typing import Optional, Dict, Callable

class ExtendedWebSocket:
    def __init__(self, symbol: str = None):
        self.symbol = symbol or os.getenv("EXTENDED_SYMBOL", "BTC-USD")
        self.api_key = os.getenv("X10_API_KEY")
        self.base_host = os.getenv("EXTENDED_WS_HOST", "wss://api.extended.exchange")
        self.ws_url = f"{self.base_host}/stream.extended.exchange/v1/orderbooks/{self.symbol}?depth=1"
        
        self.ws = None
        self.running = False
        self.thread = None
        
        self.last_bid = None
        self.last_ask = None
        self.last_update = None
        
        self.on_price_update = None

    def build_headers(self):
        headers = ["User-Agent: ExtendedWS/1.0"]
        if self.api_key:
            headers.append(f"X-Api-Key: {self.api_key}")
        return headers

    def get_current_prices(self) -> Dict:
        if not self.last_bid or not self.last_ask:
            raise ValueError("No price data available yet")
        return {
            "bid": self.last_bid,
            "ask": self.last_ask,
            "mid": (self.last_bid + self.last_ask) / 2,
            "spread": self.last_ask - self.last_bid,
            "last_update": self.last_update
        }

    def on_message(self, ws, message):
        data = json.loads(message)
        d = data["data"]
        bids = d["b"]
        asks = d["a"]
        
        def extract_price(side):
            if not side:
                raise ValueError("Empty orderbook side")
            first = side[0]
            if isinstance(first, dict):
                p = first.get("price") or first.get("p")
            elif isinstance(first, (list, tuple)):
                p = first[0]
            else:
                raise ValueError(f"Unexpected orderbook format: {first}")
            return float(p)
        
        bid = extract_price(bids)
        ask = extract_price(asks)
        
        self.last_bid = bid
        self.last_ask = ask
        self.last_update = time.time()
        
        if self.on_price_update:
            self.on_price_update(self.get_current_prices())

    def on_error(self, ws, error):
        print(f"WS error: {error}")

    def on_close(self, ws, code, msg):
        print("WS closed, reconnecting...")
        self.running = False

    def on_open(self, ws):
        print(f"WS connected for {self.symbol}")

    def run_forever(self):
        while self.running:
            try:
                self.ws = websocket.WebSocketApp(
                    self.ws_url,
                    header=self.build_headers(),
                    on_open=self.on_open,
                    on_message=self.on_message,
                    on_error=self.on_error,
                    on_close=self.on_close,
                )
                self.ws.run_forever(ping_interval=20, ping_timeout=10)
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"WS connection failed: {e}")
            
            if self.running:
                time.sleep(2)

    def start(self, callback: Optional[Callable] = None):
        if self.running:
            return
        
        self.on_price_update = callback
        self.running = True
        self.thread = threading.Thread(target=self.run_forever, daemon=True)
        self.thread.start()
        
        print(f"Started WebSocket for {self.symbol}")
        time.sleep(2)

    def stop(self):
        self.running = False
        if self.ws:
            self.ws.close()
        if self.thread:
            self.thread.join(timeout=5)
        print("WebSocket stopped")

    def wait_for_prices(self, timeout: int = 10) -> bool:
        start = time.time()
        while time.time() - start < timeout:
            if self.last_bid and self.last_ask:
                return True
            time.sleep(0.5)
        return False