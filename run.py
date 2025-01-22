# run.py
import asyncio
from app import app, application

# This ensures the application is properly initialized
loop = asyncio.get_event_loop()
loop.run_until_complete(application.initialize())
application.start()