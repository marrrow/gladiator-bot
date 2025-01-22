# app.py
import uuid
import os
import asyncio
import random
from datetime import datetime, timedelta
from collections import defaultdict
from flask import Flask, request
from telegram import Update, User, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from telegram.constants import ParseMode

# Initialize Flask app
app = Flask(__name__)
TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']  # Remove default value for security

# Initialize Telegram Application with webhook setup
async def post_init(application: Application):
    await application.bot.set_webhook("https://gladiator-bot.onrender.com/webhook")

application = Application.builder() \
    .token(TELEGRAM_TOKEN) \
    .post_init(post_init) \
    .build()

# In-memory storage
active_fights = {}
user_stats = defaultdict(lambda: {"wins": 0, "losses": 0, "rank": "Recruit", "glory": 0})

class Fight:
    def __init__(self, challenger: User, opponent: User, chat_id: int):
        self.id = str(uuid.uuid4())
        self.challenger = challenger
        self.opponent = opponent
        self.chat_id = chat_id
        self.accepted = False
        self.start_time = None
        self.end_time = None
        self.scores = {challenger.id: 0, opponent.id: 0}
        self.invitation_message_id = None

RANKS = {
    0: "Recruit",
    100: "Arena Novice",
    300: "Seasoned Fighter",
    600: "Veteran Gladiator",
    1000: "Champion",
    2000: "Arena Legend",
    5000: "Immortal Warrior"
}

VICTORY_QUOTES = [
    "𝔗𝔥𝔢 𝔠𝔯𝔬𝔴𝔡 𝔯𝔬𝔞𝔯𝔰 𝔣𝔬𝔯 {winner}! 🏛️",
    "𝔄𝔫𝔬𝔱𝔥𝔢𝔯 𝔳𝔦𝔠𝔱𝔬𝔯𝔶 𝔣𝔬𝔯 𝔱𝔥𝔢 𝔪𝔦𝔤𝔥𝔱𝔶 {winner}! ⚔️",
    "𝔗𝔥𝔢 𝔤𝔬𝔡𝔰 𝔰𝔪𝔦𝔩𝔢 𝔲𝔭𝔬𝔫 {winner} 𝔱𝔬𝔡𝔞𝔶! 🏺"
]

DEFEAT_QUOTES = [
    "𝔗𝔥𝔢 𝔠𝔯𝔬𝔴𝔡 𝔩𝔞𝔲𝔤𝔥𝔰 𝔞𝔱 {loser}'𝔰 𝔭𝔢𝔯𝔣𝔬𝔯𝔪𝔞𝔫𝔠𝔢! 😂",
    "𝔓𝔢𝔯𝔥𝔞𝔭𝔰 {loser} 𝔰𝔥𝔬𝔲𝔩𝔡 𝔱𝔯𝔶 𝔣𝔞𝔯𝔪𝔦𝔫𝔤 𝔦𝔫𝔰𝔱𝔢𝔞𝔡! 🌾",
    "𝔈𝔳𝔢𝔫 𝔱𝔥𝔢 𝔰𝔩𝔞𝔳𝔢𝔰 𝔣𝔦𝔤𝔥𝔱 𝔟𝔢𝔱𝔱𝔢𝔯 𝔱𝔥𝔞𝔫 {loser}! 🏺"
]

def calculate_glory_reward(opponent_glory: int, won: bool) -> int:
    """Calculate glory points for a fight based on opponent's glory"""
    base_reward = 20
    glory_difference = max(-500, min(500, opponent_glory - 100))
    multiplier = 1 + (glory_difference / 1000)
    reward = int(base_reward * multiplier)
    return reward if won else -int(reward * 0.5)

def get_rank(glory: int) -> str:
    """Get rank based on glory points"""
    current_rank = RANKS[0]
    for required_glory, rank in sorted(RANKS.items()):
        if glory >= required_glory:
            current_rank = rank
    return current_rank

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "*Welcome to the Arena!* 🏛️\n\n"
        "Challenge others to glorious combat:\n"
        "⚔️ `/fight @username` - Challenge someone\n"
        "📊 `/stats` - View your combat record\n"
        "🏆 `/leaderboard` - See top gladiators\n\n"
        "_Glory awaits in the arena!_",
        parse_mode=ParseMode.MARKDOWN
    )

async def fight_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    challenger = update.effective_user
    
    if not context.args:
        await update.message.reply_text("*Usage:* `/fight @username`", parse_mode=ParseMode.MARKDOWN)
        return
        
    opponent_username = context.args[0].replace("@", "")
    
    # Create fight instance
    fight = Fight(
        challenger=challenger,
        opponent=User(id=0, is_bot=False, first_name=opponent_username),
        chat_id=update.effective_chat.id
    )
    
    keyboard = [[
        InlineKeyboardButton("⚔️ Accept Challenge", callback_data=f"accept_{fight.id}"),
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    challenger_rank = get_rank(user_stats[challenger.id]["glory"])
    msg = await update.message.reply_text(
        f"⚔️ *Arena Challenge* ⚔️\n\n"
        f"*{challenger.first_name}* _{challenger_rank}_\n"
        f"challenges\n"
        f"*{opponent_username}* to combat!\n\n"
        "_You have 10 seconds to accept..._",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    
    fight.invitation_message_id = msg.message_id
    active_fights[fight.id] = fight
    
    # Auto-decline after 10 seconds
    await asyncio.sleep(10)
    if fight.id in active_fights and not active_fights[fight.id].accepted:
        await context.bot.edit_message_text(
            f"❌ {opponent_username} was too afraid to fight!",
            chat_id=update.effective_chat.id,
            message_id=msg.message_id
        )
        del active_fights[fight.id]

async def accept_fight_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    fight_id = query.data.split("_")[1]
    
    if fight_id not in active_fights:
        await query.answer("This challenge has expired!")
        return
        
    fight = active_fights[fight_id]
    fight.accepted = True
    fight.start_time = datetime.now()
    fight.end_time = fight.start_time + timedelta(seconds=10)
    
    keyboard = [[
        InlineKeyboardButton("🗡️ STRIKE! 🗡️", callback_data=f"tap_{fight_id}")
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.edit_message_text(
        "⚔️ *The Fight Begins!* ⚔️\n\n"
        "_Strike fast and true!_\n"
        "*Time remaining: 10s*",
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    
    # End fight after 10 seconds
    await asyncio.sleep(10)
    await end_fight(fight, context.bot)

async def tap_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    fight_id = query.data.split("_")[1]
    
    if fight_id not in active_fights:
        await query.answer("The battle has ended!")
        return
        
    fight = active_fights[fight_id]
    user_id = query.from_user.id
    
    if user_id not in fight.scores:
        await query.answer("You're not part of this battle!")
        return
        
    if datetime.now() > fight.end_time:
        await query.answer("Time's up!")
        return
        
    fight.scores[user_id] += 1
    await query.answer(f"Strikes: {fight.scores[user_id]}")

async def end_fight(fight: Fight, bot):
    if fight.id not in active_fights:
        return
        
    scores = fight.scores
    winner_id = max(scores, key=scores.get)
    loser_id = min(scores, key=scores.get)
    
    winner_name = fight.challenger.first_name if winner_id == fight.challenger.id else fight.opponent.first_name
    loser_name = fight.challenger.first_name if loser_id == fight.challenger.id else fight.opponent.first_name
    
    # Calculate glory changes
    glory_change = calculate_glory_reward(
        user_stats[loser_id]["glory"],
        True
    )
    
    # Update stats
    user_stats[winner_id]["wins"] += 1
    user_stats[winner_id]["glory"] += glory_change
    user_stats[loser_id]["losses"] += 1
    user_stats[loser_id]["glory"] = max(0, user_stats[loser_id]["glory"] - int(glory_change * 0.5))
    
    # Update ranks
    winner_rank = get_rank(user_stats[winner_id]["glory"])
    loser_rank = get_rank(user_stats[loser_id]["glory"])
    
    victory_quote = random.choice(VICTORY_QUOTES).format(winner=winner_name)
    defeat_quote = random.choice(DEFEAT_QUOTES).format(loser=loser_name)
    
    await bot.edit_message_text(
        f"🏛️ *Battle Results* 🏛️\n\n"
        f"*{winner_name}* _{winner_rank}_\n"
        f"Strikes: {scores[winner_id]}\n"
        f"Glory: +{glory_change}\n\n"
        f"*{loser_name}* _{loser_rank}_\n"
        f"Strikes: {scores[loser_id]}\n"
        f"Glory: {-int(glory_change * 0.5)}\n\n"
        f"_{victory_quote}_\n"
        f"_{defeat_quote}_",
        chat_id=fight.chat_id,
        message_id=fight.invitation_message_id,
        parse_mode=ParseMode.MARKDOWN
    )
    
    del active_fights[fight.id]

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    stats = user_stats[user_id]
    rank = get_rank(stats["glory"])
    
    next_rank = None
    next_rank_glory = None
    for required_glory, r in sorted(RANKS.items()):
        if required_glory > stats["glory"]:
            next_rank = r
            next_rank_glory = required_glory
            break
    
    stats_message = (
        f"🏛️ *Gladiator Status: {update.effective_user.first_name}* 🏛️\n\n"
        f"*Rank:* {rank}\n"
        f"*Glory:* {stats['glory']}\n"
        f"*Victories:* {stats['wins']}\n"
        f"*Defeats:* {stats['losses']}\n"
    )
    
    if next_rank:
        glory_needed = next_rank_glory - stats["glory"]
        stats_message += f"\n_Need {glory_needed} more glory for {next_rank}_"
    
    await update.message.reply_text(stats_message, parse_mode=ParseMode.MARKDOWN)

async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sorted_warriors = sorted(
        user_stats.items(),
        key=lambda x: (x[1]["glory"], x[1]["wins"]),
        reverse=True
    )[:10]
    
    leaderboard_text = "🏆 *Arena Champions* 🏆\n\n"
    for i, (user_id, stats) in enumerate(sorted_warriors, 1):
        user = await context.bot.get_chat_member(update.effective_chat.id, user_id)
        leaderboard_text += (
            f"{i}. *{user.user.first_name}*\n"
            f"   _{get_rank(stats['glory'])}_ - {stats['glory']} glory\n"
            f"   W: {stats['wins']} L: {stats['losses']}\n\n"
        )
    
    await update.message.reply_text(leaderboard_text, parse_mode=ParseMode.MARKDOWN)

# Register handlers
application.add_handler(CommandHandler('start', start_command))
application.add_handler(CommandHandler('fight', fight_command))
application.add_handler(CommandHandler('stats', stats_command))
application.add_handler(CommandHandler('leaderboard', leaderboard_command))
application.add_handler(CallbackQueryHandler(accept_fight_callback, pattern='^accept_'))
application.add_handler(CallbackQueryHandler(tap_callback, pattern='^tap_'))

@app.route('/webhook', methods=['POST'])
async def webhook():
    """Handle incoming updates from Telegram"""
    if request.method == "POST":
        try:
            json_data = await request.get_json()
            update = Update.de_json(json_data, application.bot)
            await application.process_update(update)
            return "ok"
        except Exception as e:
            print(f"Webhook error: {str(e)}")
            return "error", 500
    return "ok"

@app.route('/')
def home():
    return "Gladiator Bot Running 🏛️⚔️"

if __name__ == '__main__':
    from hypercorn.asyncio import serve
    from hypercorn.config import Config
    config = Config()
    config.bind = ["0.0.0.0:8000"]
    asyncio.run(serve(app, config))