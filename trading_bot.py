#!/usr/bin/env python3

import time
from dotenv import load_dotenv
from nice_funcs import ExtendedExchangeAPI
from extended_ws import ExtendedWebSocket

# Load environment variables
load_dotenv()

# ========== CONFIGURATION ==========
POSITION_SIZE_USD = 100  # Position size in USD
TAKE_PROFIT = 2.0  # Take profit at 2% gain
STOP_LOSS = -1.0  # Stop loss at 1% loss
SYMBOL = "BTC-USD"  # Change to "ETH-USD", "SOL-USD", etc.
LEVERAGE = 2  # Leverage to use for positions
LOOP_SLEEP = 2  # Sleep time between loops (seconds)

# ========== HELPER FUNCTIONS ==========

def print_header():
    print("\n" + "="*60)
    print(f"       EXTENDED EXCHANGE TRADING BOT")
    print(f"       Symbol: {SYMBOL} | Leverage: {LEVERAGE}x")
    print(f"       Position Size: ${POSITION_SIZE_USD}")
    print(f"       TP: {TAKE_PROFIT}% | SL: {STOP_LOSS}%")
    print("="*60)

def print_menu():
    print("\n📊 TRADING MENU:")
    print("  [0] Close Position")
    print("  [1] Open Long (Buy at Bid)")
    print("  [2] Open Short (Sell at Ask)")
    print("  [3] P&L Monitor (TP/SL)")
    print("  [Q] Quit")
    print("-"*40)

def display_position_status(api: ExtendedExchangeAPI):
    _, im_in_pos, mypos_size, pos_sym, entry_px, pnl_perc, is_long, unrealized_pnl = api.get_position(SYMBOL)
    
    if im_in_pos:
        position_type = "LONG" if is_long else "SHORT"
        print(f"\n📈 Current Position:")
        print(f"   Type: {position_type}")
        print(f"   Size: {abs(mypos_size)} {SYMBOL}")
        print(f"   Entry: ${entry_px:,.2f}")
        print(f"   P&L: {pnl_perc:.2f}% (${unrealized_pnl:.2f})")
    else:
        print("\n📊 No position open")

def display_current_prices(ws: ExtendedWebSocket):
    prices = ws.get_current_prices()
    if prices['bid'] and prices['ask']:
        print(f"\n💱 Current Prices:")
        print(f"   Bid: ${prices['bid']:,.2f}")
        print(f"   Ask: ${prices['ask']:,.2f}")
        print(f"   Spread: ${prices['spread']:.2f}")

def entry_loop(api: ExtendedExchangeAPI, ws: ExtendedWebSocket, side: str) -> bool:
    """
    Loop to enter position with limit orders at bid/ask
    Returns True if position opened successfully
    """
    print(f"\n🎯 Opening {side.upper()} position with {LEVERAGE}x leverage...")
    
    # Convert USD to asset size
    asset_size = api.usd_to_asset_size(SYMBOL, POSITION_SIZE_USD)
    if asset_size <= 0:
        print("❌ Failed to calculate asset size")
        return False
    
    max_attempts = 10
    attempt = 0
    
    while attempt < max_attempts:
        attempt += 1
        print(f"\n📍 Attempt {attempt}/{max_attempts}")
        
        # Check if we already have a position
        _, im_in_pos, current_size, _, _, _, _, _ = api.get_position(SYMBOL)
        if im_in_pos:
            print(f"✅ Position already open: {abs(current_size)} {SYMBOL}")
            return True
        
        # Get current prices from WebSocket
        prices = ws.get_current_prices()
        if not prices['bid'] or not prices['ask']:
            print("⏳ Waiting for price data...")
            time.sleep(LOOP_SLEEP)
            continue
        
        # Place limit order at favorable price
        if side == "long":
            # For long: place buy order at bid price
            order_price = prices['bid']
            print(f"   Placing BUY order: {asset_size} @ ${order_price:,.2f}")
            order = api.buy_limit(SYMBOL, asset_size, order_price, LEVERAGE)
        else:
            # For short: place sell order at ask price  
            order_price = prices['ask']
            print(f"   Placing SELL order: {asset_size} @ ${order_price:,.2f}")
            order = api.sell_limit(SYMBOL, asset_size, order_price, LEVERAGE)
        
        if order:
            order_id = order.get('order_id') or order.get('id')
            print(f"   Order placed: {order_id}")
        else:
            print("   Failed to place order")
            time.sleep(LOOP_SLEEP)
            continue
        
        # Wait and check if order filled
        time.sleep(LOOP_SLEEP * 2)
        
        # Check position again
        _, im_in_pos, current_size, _, _, _, _, _ = api.get_position(SYMBOL)
        if im_in_pos:
            print(f"✅ Position opened: {abs(current_size)} {SYMBOL}")
            return True
        
        # Check order status
        is_filled, remaining = api.check_order_filled(order_id)
        
        if is_filled:
            print("   Order filled, checking position...")
            time.sleep(1)
            _, im_in_pos, current_size, _, _, _, _, _ = api.get_position(SYMBOL)
            if im_in_pos:
                print(f"✅ Position confirmed: {abs(current_size)} {SYMBOL}")
                return True
        else:
            print(f"   Order not filled, remaining: {remaining}")
            # Cancel unfilled order
            api.cancel_all_orders(SYMBOL)
            print("   Cancelled unfilled order")
        
        # Update size for next attempt if partially filled
        if remaining > 0 and remaining < asset_size:
            asset_size = remaining
            print(f"   Adjusting size for next attempt: {asset_size}")
        
        time.sleep(LOOP_SLEEP)
    
    print("❌ Failed to open position after max attempts")
    return False

def exit_loop(api: ExtendedExchangeAPI, ws: ExtendedWebSocket) -> bool:
    """
    Loop to exit position with limit orders
    Returns True if position closed successfully
    """
    print("\n🎯 Closing position...")
    
    max_attempts = 20
    attempt = 0
    
    while attempt < max_attempts:
        attempt += 1
        print(f"\n📍 Attempt {attempt}/{max_attempts}")
        
        # Check current position
        _, im_in_pos, mypos_size, _, _, pnl_perc, is_long, _ = api.get_position(SYMBOL)
        
        if not im_in_pos:
            print("✅ Position closed successfully!")
            return True
        
        close_size = abs(mypos_size)
        print(f"   Position to close: {'LONG' if is_long else 'SHORT'} {close_size}")
        print(f"   Current P&L: {pnl_perc:.2f}%")
        
        # Get current prices
        prices = ws.get_current_prices()
        if not prices['bid'] or not prices['ask']:
            print("⏳ Waiting for price data...")
            time.sleep(LOOP_SLEEP)
            continue
        
        # Place aggressive limit order to close
        if is_long:
            # Close long: sell at bid or slightly below
            order_price = prices['bid'] * 0.9995
            print(f"   Placing SELL order: {close_size} @ ${order_price:,.2f}")
            order = api.sell_limit(SYMBOL, close_size, order_price, 1)  # No leverage for closing
        else:
            # Close short: buy at ask or slightly above
            order_price = prices['ask'] * 1.0005
            print(f"   Placing BUY order: {close_size} @ ${order_price:,.2f}")
            order = api.buy_limit(SYMBOL, close_size, order_price, 1)  # No leverage for closing
        
        if order:
            order_id = order.get('order_id') or order.get('id')
            print(f"   Order placed: {order_id}")
        else:
            print("   Failed to place order")
            time.sleep(LOOP_SLEEP)
            continue
        
        # Wait for order to fill
        time.sleep(LOOP_SLEEP * 2)
        
        # Check if position closed
        _, still_in_pos, remaining_size, _, _, _, _, _ = api.get_position(SYMBOL)
        
        if not still_in_pos:
            print("✅ Position closed successfully!")
            return True
        
        if abs(remaining_size) < close_size:
            print(f"   Partially closed. Remaining: {abs(remaining_size)}")
            close_size = abs(remaining_size)
        
        # Cancel unfilled orders
        api.cancel_all_orders(SYMBOL)
        
        time.sleep(LOOP_SLEEP)
    
    # Last resort: try market order
    print("\n⚠️ Max attempts reached, trying market close...")
    return api.close_position(SYMBOL)

def pnl_monitor_loop(api: ExtendedExchangeAPI, ws: ExtendedWebSocket):
    """
    Monitor position P&L and close when TP/SL hit
    """
    print(f"\n📊 P&L Monitor Active")
    print(f"   Take Profit: {TAKE_PROFIT}%")
    print(f"   Stop Loss: {STOP_LOSS}%")
    print("   Press Ctrl+C to stop monitoring\n")
    
    while True:
        try:
            # Check position
            _, im_in_pos, mypos_size, _, entry_px, pnl_perc, is_long, unrealized_pnl = api.get_position(SYMBOL)
            
            if not im_in_pos:
                print("📊 No position to monitor")
                break
            
            # Display current status
            position_type = "LONG" if is_long else "SHORT"
            
            # Get current prices for display
            prices = ws.get_current_prices()
            current_price = prices['mid'] if prices['mid'] else 0
            
            # Clear line and print status
            status = f"[{time.strftime('%H:%M:%S')}] {position_type} {abs(mypos_size):.4f} | "
            status += f"Entry: ${entry_px:,.2f} | Current: ${current_price:,.2f} | "
            status += f"P&L: {pnl_perc:+.2f}% (${unrealized_pnl:+.2f})"
            
            # Color code based on P&L
            if pnl_perc > 0:
                print(f"✅ {status}")
            elif pnl_perc < 0:
                print(f"❌ {status}")
            else:
                print(f"➖ {status}")
            
            # Check TP/SL
            if pnl_perc >= TAKE_PROFIT:
                print(f"\n🎯 TAKE PROFIT HIT! P&L: {pnl_perc:.2f}%")
                if exit_loop(api, ws):
                    print("✅ Position closed at profit!")
                break
            
            if pnl_perc <= STOP_LOSS:
                print(f"\n🛑 STOP LOSS HIT! P&L: {pnl_perc:.2f}%")
                if exit_loop(api, ws):
                    print("✅ Position closed at loss")
                break
            
            time.sleep(LOOP_SLEEP)
        except KeyboardInterrupt:
            print("\n\n⏸️  P&L monitoring stopped")
            break

# ========== MAIN FUNCTION ==========

def main():
    print_header()
    
    # Initialize API and WebSocket
    print("\n🔧 Initializing...")
    import os
    api_key = os.getenv("X10_API_KEY")
    stark_key = os.getenv("X10_PRIVATE_KEY")
    api = ExtendedExchangeAPI(api_key, stark_key)
    ws = ExtendedWebSocket(SYMBOL)
    
    # Start WebSocket
    ws.start()
    
    # Wait for price data
    print("⏳ Waiting for price data...")
    if not ws.wait_for_prices(timeout=10):
        print("❌ Failed to get price data")
        return
    
    print("✅ Connected and ready!")
    
    try:
        while True:
            # Display current status
            display_position_status(api)
            display_current_prices(ws)
            
            # Show menu
            print_menu()
            
            # Get user input
            choice = input("Enter choice: ").strip().upper()
            
            if choice == "Q":
                print("\n👋 Goodbye!")
                break
            
            elif choice == "0":
                # Close position
                _, im_in_pos, _, _, _, _, _, _ = api.get_position(SYMBOL)
                if im_in_pos:
                    if exit_loop(api, ws):
                        print("✅ Position closed!")
                    else:
                        print("❌ Failed to close position")
                else:
                    print("📊 No position to close")
            
            elif choice == "1":
                # Open long
                _, im_in_pos, _, _, _, _, _, _ = api.get_position(SYMBOL)
                if im_in_pos:
                    print("⚠️ Position already open. Close it first.")
                else:
                    if entry_loop(api, ws, "long"):
                        print("✅ Long position opened!")
                    else:
                        print("❌ Failed to open long position")
            
            elif choice == "2":
                # Open short
                _, im_in_pos, _, _, _, _, _, _ = api.get_position(SYMBOL)
                if im_in_pos:
                    print("⚠️ Position already open. Close it first.")
                else:
                    if entry_loop(api, ws, "short"):
                        print("✅ Short position opened!")
                    else:
                        print("❌ Failed to open short position")
            
            elif choice == "3":
                # P&L Monitor
                _, im_in_pos, _, _, _, _, _, _ = api.get_position(SYMBOL)
                if im_in_pos:
                    pnl_monitor_loop(api, ws)
                else:
                    print("📊 No position to monitor")
            
            else:
                print("❌ Invalid choice. Please try again.")
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n⏸️  Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        # Cleanup
        ws.stop()
        api.cleanup()
        print("\n✅ Cleanup complete")

if __name__ == "__main__":
    main()