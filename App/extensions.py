import os

from flask import current_app
import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

redis_client = redis.from_url(REDIS_URL)


def cleanup_expired_sessions():
    """
    Function to clean up expired sessions
    This can be run periodically using a scheduler or cron job
    """
    pattern = "discofy:state:*"
    keys = redis_client.keys(pattern)
    count = 0

    for key in keys:
        ttl = redis_client.ttl(key)
        if ttl <= 0:  # Already expired or no expiry
            redis_client.delete(key)
            count += 1

    print(f"Cleaned up {count} expired sessions")
    return count
