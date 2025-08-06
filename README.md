# Telegram CC Checker Bot 🔒

A Telegram bot for validating credit card information using the Luhn algorithm and various card type detection patterns.

## ⚠️ Disclaimer
This bot is for **educational purposes only**. Never use real credit card information with any online service or bot.

## Features

✅ **Luhn Algorithm Validation** - Mathematically validates card numbers  
✅ **Card Type Detection** - Supports Visa, Mastercard, Amex, Discover, JCB, Diners, UnionPay  
✅ **Expiry Date Validation** - Checks if expiry date is in the future  
✅ **CVV Format Validation** - Validates CVV length and format  
✅ **Rate Limiting** - Prevents abuse (10 requests/minute per user)  
✅ **Multiple Input Formats** - Supports various card data formats  

## Quick Setup

1. **Clone and install dependencies:**
```bash
git clone <your-repo>
cd telegram-bot
pip install -r requirements.txt
```

2. **Create your bot:**
   - Message [@BotFather](https://t.me/BotFather) on Telegram
   - Send `/newbot` and follow instructions
   - Copy your bot token

3. **Configure:**
```bash
cp .env.example .env
# Edit .env and add your TELEGRAM_BOT_TOKEN
```

4. **Run:**
```bash
python app.py
```

## Usage

Send any of these formats to the bot:
- `4111111111111111 12/25 123`
- `4111111111111111|12|25|123`  
- `4111111111111111/12/25/123`
- `/check 4111111111111111 12/25 123`

## Commands
- `/start` - Welcome message
- `/help` - Detailed help
- `/check` - Check card details

## Test Cards
```
Visa: 4111111111111111
Mastercard: 5555555555554444
Amex: 378282246310005
Discover: 6011111111111117
```

## Security Features
- Rate limiting (10 requests/minute)
- Card number masking in responses
- No data storage or logging of card details
- Input validation and sanitization