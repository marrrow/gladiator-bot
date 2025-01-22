from app import application
import os

async def set_webhook():
    await application.bot.set_webhook(
        url="https://gladiator-bot.onrender.com/webhook"
    )

if __name__ == '__main__':
    import asyncio
    asyncio.run(set_webhook())