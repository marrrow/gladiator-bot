from app import application
import asyncio

async def main():
    await application.start()
    await application.bot.set_webhook(
        "https://gladiator-bot.onrender.com/webhook"
    )

if __name__ == '__main__':
    asyncio.run(main())