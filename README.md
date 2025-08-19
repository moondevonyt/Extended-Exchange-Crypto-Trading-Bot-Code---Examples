# Extended Exchange Trading Bot 🚀

**Built by MoonDev** | [YouTube Channel](https://www.youtube.com/@moondevonyt)

A professional cryptocurrency trading bot for Extended Exchange with real-time WebSocket price feeds, limit order execution, and automated P&L management.

## Features 🌟

- **Real-time WebSocket Price Feeds** - Lightning-fast price updates for optimal entry/exit
- **Interactive Menu System** - Simple number-based controls for all trading operations
- **Smart Order Management** - Limit orders with automatic fill checking and size adjustment
- **P&L Monitoring** - Automated take profit and stop loss with real-time tracking
- **Position Management** - Long and short positions with precise entry/exit loops

## Menu Options 📊

- **[0] Close Position** - Exit current position using limit orders
- **[1] Open Long** - Buy at bid price (maker order)
- **[2] Open Short** - Sell at ask price (maker order)  
- **[3] P&L Monitor** - Auto-close at take profit/stop loss
- **[Q] Quit** - Exit the bot

## Installation 📦

1. Clone this repository:
```bash
git clone https://github.com/yourusername/Extended-Exchange-Crypto-Trading-Bot-Code---Examples.git
cd Extended-Exchange-Crypto-Trading-Bot-Code---Examples
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your environment variables:
```bash
cp .env.example .env
```

4. Edit `.env` with your Extended Exchange credentials

## Configuration ⚙️

### Environment Variables (.env)

**IMPORTANT:** All Extended Exchange API variables MUST start with `X10_` prefix:

```env
# Required - Get these from Extended Exchange
X10_API_KEY=your_api_key_here
X10_PRIVATE_KEY=your_stark_private_key_here  
X10_PUBLIC_KEY=your_stark_public_key_here
X10_VAULT_ID=your_vault_id_here

# Optional - Defaults shown
X10_BASE_URL=https://api.extended.exchange
EXTENDED_WS_HOST=wss://api.extended.exchange
EXTENDED_SYMBOL=BTC-USD
```

⚠️ **Note:** The `X10_` prefix is required for all API-related environment variables. This is a quirk of the Extended Exchange SDK.

### Bot Settings

Edit these constants at the top of `trading_bot.py`:

```python
POSITION_SIZE_USD = 100  # Position size in USD
TAKE_PROFIT = 2.0        # Take profit at 2% gain
STOP_LOSS = -1.0         # Stop loss at 1% loss
LOOP_SLEEP = 2           # Sleep between loops (seconds)
```

## Usage 🎮

Run the bot:
```bash
python trading_bot.py
```

### Trading Flow

1. **Entry**: Places limit orders at bid (long) or ask (short)
   - Loops until filled
   - Adjusts size for partial fills
   - Cancels and replaces stale orders

2. **Exit**: Uses limit orders with aggressive pricing
   - Loops until position closed
   - Handles partial fills
   - Falls back to market orders if needed

3. **P&L Monitor**: Continuously tracks position
   - Auto-closes at take profit
   - Auto-closes at stop loss
   - Shows real-time P&L updates

## Files 📁

- `trading_bot.py` - Main bot with interactive menu
- `nice_funcs.py` - Extended Exchange API wrapper
- `extended_ws.py` - WebSocket handler for real-time prices
- `.env.example` - Environment variable template
- `requirements.txt` - Python dependencies

## Safety Features 🛡️

- Limit orders only (no market slippage)
- Position size validation
- Automatic order cancellation on errors
- Real-time position tracking
- Partial fill handling

## Support 💬

For tutorials and updates:
- 🎥 [MoonDev YouTube](https://www.youtube.com/@moondevonyt)
- 📺 Watch the build process and live trading sessions

## Known Issues 🔧

**Error 1145: "Non reduce-only orders are not allowed"**
- This means your Extended Exchange account has zero balance or is restricted
- Add funds to your account to resolve this
- The bot code is working correctly - this is an account-level restriction

## Disclaimer ⚠️

This bot is for educational purposes. Trading cryptocurrency carries significant risk. Only trade with funds you can afford to lose. Always test on testnet first.

## License 📄

MIT License - See LICENSE file for details

---

**Built with 🌙 by MoonDev**