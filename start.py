#!/usr/bin/env python3
"""Startup script for Render deployment."""

import asyncio
import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.main import main

if __name__ == "__main__":
    # Set environment variables for Render
    os.environ.setdefault('MODE', 'polling')
    os.environ.setdefault('LOG_LEVEL', 'INFO')
    
    # Run the bot
    asyncio.run(main())

