import asyncio
from app import app, application

# Initialize the bot application
loop = asyncio.get_event_loop()
loop.run_until_complete(application.initialize())
application.start()