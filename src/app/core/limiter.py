from slowapi import Limiter
from slowapi.util import get_remote_address

# Define the rate limiter instance
# key_func determines how clients are identified (e.g., by IP)
# default_limits applies to all routes unless overridden
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"]) 