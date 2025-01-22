from app import application
import os

async def main():
    await application.bot.set_webhook(
        url="https://gladiator-bot.onrender.com/webhook"
    )

if __name__ == '__main__':
    application.run_polling()