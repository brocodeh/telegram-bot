import os
import re
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.constants import ParseMode
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class CCChecker:
    def __init__(self):
        self.card_types = {
            'visa': [r'^4[0-9]{12}(?:[0-9]{3})?$'],
            'mastercard': [r'^5[1-5][0-9]{14}$', r'^2[2-7][0-9]{14}$'],
            'amex': [r'^3[47][0-9]{13}$'],
            'discover': [r'^6(?:011|5[0-9]{2})[0-9]{12}$'],
            'diners': [r'^3[0689][0-9]{11}$'],
            'jcb': [r'^(?:2131|1800|35\d{3})\d{11}$'],
            'unionpay': [r'^(62|88)[0-9]{14,17}$']
        }
        
        # Rate limiting: user_id -> list of timestamps
        self.rate_limit_data = defaultdict(list)
        self.max_requests_per_minute = 10
        
    def luhn_check(self, card_number: str) -> bool:
        """Validate credit card number using Luhn algorithm"""
        def digits_of(n):
            return [int(d) for d in str(n)]
        
        digits = digits_of(card_number)
        odd_digits = digits[-1::-2]
        even_digits = digits[-2::-2]
        checksum = sum(odd_digits)
        for d in even_digits:
            checksum += sum(digits_of(d*2))
        return checksum % 10 == 0
    
    def detect_card_type(self, card_number: str) -> Optional[str]:
        """Detect the type of credit card"""
        for card_type, patterns in self.card_types.items():
            for pattern in patterns:
                if re.match(pattern, card_number):
                    return card_type
        return None
    
    def validate_expiry(self, month: str, year: str) -> bool:
        """Validate expiry date"""
        try:
            month = int(month)
            year = int(year)
            
            # Handle 2-digit years
            if year < 100:
                year += 2000
                
            if month < 1 or month > 12:
                return False
                
            expiry_date = datetime(year, month, 1)
            current_date = datetime.now().replace(day=1)
            
            return expiry_date >= current_date
        except ValueError:
            return False
    
    def is_rate_limited(self, user_id: int) -> bool:
        """Check if user is rate limited"""
        now = datetime.now()
        user_requests = self.rate_limit_data[user_id]
        
        # Remove old requests (older than 1 minute)
        user_requests[:] = [req_time for req_time in user_requests if now - req_time < timedelta(minutes=1)]
        
        if len(user_requests) >= self.max_requests_per_minute:
            return True
            
        user_requests.append(now)
        return False
    
    def check_card(self, card_data: str) -> Dict:
        """Main card checking function"""
        # Parse card data (supports multiple formats)
        parts = card_data.replace('|', ' ').replace('/', ' ').replace('-', ' ').split()
        
        if len(parts) < 1:
            return {'valid': False, 'error': 'Invalid format'}
        
        card_number = re.sub(r'\D', '', parts[0])  # Remove non-digits
        
        if len(card_number) < 13 or len(card_number) > 19:
            return {'valid': False, 'error': 'Invalid card number length'}
        
        # Check Luhn algorithm
        luhn_valid = self.luhn_check(card_number)
        card_type = self.detect_card_type(card_number)
        
        result = {
            'card_number': card_number,
            'luhn_valid': luhn_valid,
            'card_type': card_type,
            'valid': luhn_valid and card_type is not None
        }
        
        # Check expiry if provided
        if len(parts) >= 2:
            exp_parts = parts[1].split('/')
            if len(exp_parts) == 2:
                month, year = exp_parts
                expiry_valid = self.validate_expiry(month, year)
                result['expiry_valid'] = expiry_valid
                result['expiry'] = f"{month}/{year}"
        
        # Check CVV if provided
        if len(parts) >= 3:
            cvv = parts[2]
            cvv_valid = len(cvv) in [3, 4] and cvv.isdigit()
            result['cvv_valid'] = cvv_valid
            result['cvv'] = cvv
            
        return result

# Initialize CC checker
cc_checker = CCChecker()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    welcome_text = """
🔒 **CC Checker Bot** 🔒

Welcome! I can help you validate credit card information.

**Commands:**
/start - Show this welcome message
/help - Show detailed help
/check - Check a credit card

**Supported formats:**
• `4111111111111111 12/25 123`
• `4111111111111111|12|25|123`
• `4111111111111111/12/25/123`

**Features:**
✅ Luhn algorithm validation
✅ Card type detection (Visa, Mastercard, Amex, etc.)
✅ Expiry date validation
✅ CVV format validation
✅ Rate limiting for security

⚠️ **Disclaimer:** This bot is for educational purposes only. Do not use with real credit card data.
    """
    
    keyboard = [
        [InlineKeyboardButton("📋 Help", callback_data='help')],
        [InlineKeyboardButton("🔍 Check Card", callback_data='check')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send help information."""
    help_text = """
📖 **Detailed Help**

**How to use:**
1. Send `/check` followed by card details
2. Or just send card details directly

**Supported formats:**
```
4111111111111111 12/25 123
4111111111111111|12|25|123
4111111111111111/12/25/123
4111111111111111-12-25-123
```

**What gets checked:**
🔹 **Card Number**: Luhn algorithm validation
🔹 **Card Type**: Visa, Mastercard, Amex, Discover, etc.
🔹 **Expiry Date**: MM/YY format, future date validation
🔹 **CVV**: 3-4 digit format validation

**Rate Limits:**
• Maximum 10 requests per minute per user
• This is to prevent abuse

**Security Notice:**
⚠️ Never send real credit card information through any bot or online service. This tool is for educational and testing purposes only.
    """
    
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

async def check_card_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /check command."""
    if not context.args:
        await update.message.reply_text(
            "Please provide card details after the command.\n\n"
            "Example: `/check 4111111111111111 12/25 123`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    card_data = ' '.join(context.args)
    await process_card_check(update, card_data)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle direct card data messages."""
    message_text = update.message.text.strip()
    
    # Check if message looks like card data
    if re.search(r'\d{13,19}', message_text):
        await process_card_check(update, message_text)
    else:
        await update.message.reply_text(
            "Send card details to check, or use /help for more information.\n\n"
            "Example: `4111111111111111 12/25 123`",
            parse_mode=ParseMode.MARKDOWN
        )

async def process_card_check(update: Update, card_data: str) -> None:
    """Process card checking request."""
    user_id = update.effective_user.id
    
    # Check rate limiting
    if cc_checker.is_rate_limited(user_id):
        await update.message.reply_text(
            "⚠️ Rate limit exceeded. Please wait a minute before checking more cards."
        )
        return
    
    # Check the card
    result = cc_checker.check_card(card_data)
    
    if 'error' in result:
        await update.message.reply_text(f"❌ Error: {result['error']}")
        return
    
    # Format response
    card_num_masked = result['card_number'][:6] + '*' * (len(result['card_number']) - 10) + result['card_number'][-4:]
    
    status_emoji = "✅" if result['valid'] else "❌"
    card_type = result.get('card_type', 'Unknown').title()
    
    response = f"""
{status_emoji} **Card Check Result**

🔢 **Card**: `{card_num_masked}`
🏦 **Type**: {card_type}
✨ **Luhn**: {'Valid' if result['luhn_valid'] else 'Invalid'}
"""
    
    if 'expiry' in result:
        expiry_status = "✅ Valid" if result.get('expiry_valid', False) else "❌ Invalid"
        response += f"📅 **Expiry**: {result['expiry']} ({expiry_status})\n"
    
    if 'cvv' in result:
        cvv_status = "✅ Valid" if result.get('cvv_valid', False) else "❌ Invalid"
        response += f"🔐 **CVV**: {'*' * len(result['cvv'])} ({cvv_status})\n"
    
    response += f"\n📊 **Overall**: {'Valid Format' if result['valid'] else 'Invalid Format'}"
    
    await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button callbacks."""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'help':
        await help_command(query, context)
    elif query.data == 'check':
        await query.message.reply_text(
            "Send me card details to check:\n\n"
            "Example: `4111111111111111 12/25 123`",
            parse_mode=ParseMode.MARKDOWN
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors."""
    logger.error(f"Update {update} caused error {context.error}")

def main() -> None:
    """Start the bot."""
    # Get bot token from environment variable
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not token:
        print("Error: TELEGRAM_BOT_TOKEN environment variable not set!")
        print("Please create a .env file with your bot token:")
        print("TELEGRAM_BOT_TOKEN=your_bot_token_here")
        return
    
    # Create the Application
    application = Application.builder().token(token).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("check", check_card_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Run the bot
    print("🤖 CC Checker Bot is starting...")
    print("Press Ctrl+C to stop the bot")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
