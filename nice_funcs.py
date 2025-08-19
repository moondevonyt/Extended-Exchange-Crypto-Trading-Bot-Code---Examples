import requests
import json
import time
import os
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
import asyncio
from x10.perpetual.trading_client import PerpetualTradingClient
from x10.perpetual.configuration import TESTNET_CONFIG, MAINNET_CONFIG
from x10.perpetual.orders import OrderSide
from x10.perpetual.accounts import StarkPerpetualAccount

class ExtendedExchangeAPI:
    def __init__(self, api_key: str = None, stark_key: str = None):
        self.api_key = api_key or os.getenv("X10_API_KEY")
        self.stark_key = stark_key or os.getenv("X10_PRIVATE_KEY")
        self.base_url = os.getenv("X10_BASE_URL", "https://api.extended.exchange")
        
        self.use_testnet = "testnet" in self.base_url.lower()
        self.config = TESTNET_CONFIG if self.use_testnet else MAINNET_CONFIG
        
        vault_id = int(os.getenv("X10_VAULT_ID"))
        private_key = os.getenv("X10_PRIVATE_KEY", stark_key)
        public_key = os.getenv("X10_PUBLIC_KEY")
        
        self.stark_account = StarkPerpetualAccount(
            vault=vault_id,
            private_key=private_key,
            public_key=public_key,
            api_key=self.api_key
        )
        
        self.trading_client = PerpetualTradingClient(self.config, self.stark_account)
        
        self.session = requests.Session()
        self.session.headers.update({
            "X-Api-Key": self.api_key,
            "User-Agent": "extended-trading-bot/1.0",
            "Content-Type": "application/json"
        })
        
        self._event_loop = None
    
    def __del__(self):
        """Cleanup on deletion"""
        self.cleanup()
    
    def cleanup(self):
        """Close event loop and sessions properly"""
        try:
            if self._event_loop and not self._event_loop.is_closed():
                # Close any pending tasks
                pending = asyncio.all_tasks(self._event_loop)
                for task in pending:
                    task.cancel()
                # Give tasks time to cancel
                self._event_loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                # Close the loop
                self._event_loop.close()
        except:
            pass  # Ignore cleanup errors
        try:
            if self.session:
                self.session.close()
        except:
            pass

    def _get_event_loop(self):
        if self._event_loop is None or self._event_loop.is_closed():
            self._event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._event_loop)
        return self._event_loop

    def _request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        url = f"{self.base_url}{endpoint}"
        response = self.session.request(method, url, json=data)
        
        if not response.ok:
            print(f"Error response: {response.status_code}")
            print(f"Response content: {response.text}")
        
        response.raise_for_status()
        return response.json()

    def get_position(self, symbol: str) -> Tuple:
        loop = self._get_event_loop()
        
        async def get_pos():
            positions = await self.trading_client.account.get_positions()
            return positions
        
        positions = loop.run_until_complete(get_pos())
        
        im_in_pos = False
        mypos_size = 0
        pos_sym = None
        entry_px = 0
        pnl_perc = 0
        is_long = False
        unrealized_pnl = 0
        
        for pos in positions.data:
            market_attr = None
            if hasattr(pos, 'market_name'):
                market_attr = pos.market_name
            elif hasattr(pos, 'market'):
                market_attr = pos.market
            elif hasattr(pos, 'symbol'):
                market_attr = pos.symbol
            
            if market_attr == symbol:
                im_in_pos = True
                mypos_size = float(pos.size)
                pos_sym = market_attr
                
                if hasattr(pos, 'entry_price'):
                    entry_px = float(pos.entry_price)
                elif hasattr(pos, 'open_price'):
                    entry_px = float(pos.open_price)
                
                if hasattr(pos, 'unrealised_pnl'):
                    unrealized_pnl = float(pos.unrealised_pnl)
                
                if hasattr(pos, 'unrealized_pnl_percent'):
                    pnl_perc = float(pos.unrealized_pnl_percent)
                elif hasattr(pos, 'pnl_percent'):
                    pnl_perc = float(pos.pnl_percent)
                elif unrealized_pnl != 0 and entry_px > 0:
                    position_value = abs(mypos_size * entry_px)
                    leverage = float(pos.leverage) if hasattr(pos, 'leverage') else 1
                    initial_margin = position_value / leverage
                    pnl_perc = (unrealized_pnl / initial_margin) * 100 if initial_margin > 0 else 0
                
                if hasattr(pos, 'side'):
                    is_long = pos.side == 'LONG'
                else:
                    is_long = mypos_size > 0
                
                break
        
        return positions, im_in_pos, mypos_size, pos_sym, entry_px, pnl_perc, is_long, unrealized_pnl

    def set_leverage(self, symbol: str, leverage: int):
        """Set leverage for a symbol"""
        loop = self._get_event_loop()
        
        async def set_lev():
            return await self.trading_client.account.update_leverage(
                market_name=symbol, 
                leverage=leverage
            )
        
        return loop.run_until_complete(set_lev())

    def limit_order(self, market: str, side: str, quantity: float, price: float, leverage: int = 1) -> Dict:
        loop = self._get_event_loop()
        
        async def place_order():
            # Set leverage if provided
            if leverage > 1:
                try:
                    await self.trading_client.account.update_leverage(market_name=market, leverage=leverage)
                except Exception as e:
                    print(f"Leverage update note: {e}")
            
            order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
            rounded_price = round(price, 1)
            
            response = await self.trading_client.place_order(
                market_name=market,
                amount_of_synthetic=Decimal(str(quantity)),
                price=Decimal(str(rounded_price)),
                side=order_side,
                post_only=False,  # Changed to False - post_only might be causing the reduce-only error
            )
            return response
        
        return loop.run_until_complete(place_order())
    
    def buy_limit(self, market: str, quantity: float, price: float, leverage: int = 1) -> Dict:
        return self.limit_order(market, "buy", quantity, price, leverage)
    
    def sell_limit(self, market: str, quantity: float, price: float, leverage: int = 1) -> Dict:
        return self.limit_order(market, "sell", quantity, price, leverage)

    def cancel_all_orders(self, market: Optional[str] = None) -> Dict:
        data = {}
        if market:
            data["market"] = market
        return self._request("POST", "/api/v1/user/order/massCancel", data)

    def check_order_filled(self, order_id: str) -> Tuple[bool, float]:
        # Get open orders
        params = ["status=OPEN"]
        query = "?" + "&".join(params)
        orders = self._request("GET", f"/api/v1/user/orders{query}")
        
        for order in orders.get('data', []):
            if order.get('id') == order_id or order.get('externalId') == order_id:
                filled_qty = float(order.get('filledQuantity', 0))
                total_qty = float(order.get('quantity', 0))
                
                if filled_qty >= total_qty:
                    return True, 0
                else:
                    remaining = total_qty - filled_qty
                    return False, remaining
        
        return True, 0

    def close_position(self, symbol: str) -> bool:
        _, im_in_pos, mypos_size, _, _, _, is_long, _ = self.get_position(symbol)
        
        if not im_in_pos:
            print("No position to close")
            return False
        
        self.cancel_all_orders(symbol)
        time.sleep(1)
        
        close_size = abs(mypos_size)
        
        # Use market order for closing
        loop = self._get_event_loop()
        
        async def place_order():
            order_side = OrderSide.SELL if is_long else OrderSide.BUY
            
            orderbook = await self.trading_client.markets_info.get_orderbook_snapshot(market_name=symbol)
            
            if is_long:
                aggressive_price = float(orderbook.data.bid[0].price) * 0.99
            else:
                aggressive_price = float(orderbook.data.ask[0].price) * 1.01
            
            aggressive_price = round(aggressive_price, 1)
            
            response = await self.trading_client.place_order(
                market_name=symbol,
                amount_of_synthetic=Decimal(str(close_size)),
                price=Decimal(str(aggressive_price)),
                side=order_side,
                post_only=False,
            )
            return response
        
        result = loop.run_until_complete(place_order())
        print(f"Close order result: {result}")
        
        time.sleep(2)
        _, still_in_pos, _, _, _, _, _, _ = self.get_position(symbol)
        
        if not still_in_pos:
            print("Position successfully closed!")
            return True
        else:
            print("Position may still exist, checking again...")
            return False

    def usd_to_asset_size(self, symbol: str, usd_amount: float) -> float:
        # Get current prices
        loop = self._get_event_loop()
        
        async def get_prices():
            orderbook = await self.trading_client.markets_info.get_orderbook_snapshot(market_name=symbol)
            return {
                "bid": float(orderbook.data.bid[0].price) if orderbook.data.bid else 0.0,
                "ask": float(orderbook.data.ask[0].price) if orderbook.data.ask else 0.0
            }
        
        bid_ask = loop.run_until_complete(get_prices())
        mid_price = (bid_ask['bid'] + bid_ask['ask']) / 2
        
        if mid_price <= 0:
            raise ValueError(f"Invalid price for {symbol}: {mid_price}")
        
        asset_size = usd_amount / mid_price
        
        if 'BTC' in symbol:
            asset_size = round(asset_size, 3)
            if asset_size == 0.0 and usd_amount > 0:
                asset_size = 0.001
        elif 'ETH' in symbol:
            asset_size = round(asset_size, 4)
            if asset_size == 0 and usd_amount > 0:
                asset_size = 0.0001
        else:
            asset_size = round(asset_size, 4)
            if asset_size == 0 and usd_amount > 0:
                asset_size = 0.0001
        
        print(f"USD to Asset: ${usd_amount} -> {asset_size} {symbol} @ ${mid_price:,.2f}")
        return asset_size