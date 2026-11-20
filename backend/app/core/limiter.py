"""
Centralized rate limiter configuration for the FastAPI application.
Prevents circular imports between API routers and the main application instance.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
