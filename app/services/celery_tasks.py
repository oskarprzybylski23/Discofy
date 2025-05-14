import os
import json

import redis
from celery import Celery

from .spotify import transfer_from_discogs

# Celery and Redis client configuration
celery = Celery(
    'discofy',
    broker=os.environ.get('REDIS_URL', 'redis://redis:6379'),
    backend=os.environ.get('REDIS_URL', 'redis://redis:6379')
)

redis_url = os.environ.get('REDIS_URL', 'redis://redis:6379')
celery_redis_client = redis.Redis.from_url(redis_url)


@celery.task(bind=True)
def transfer_collection_task(self, collection_items, access_token, progress_key):
    """
    Celery task to handle transfer of Discogs items to Spotify.
    Calls helper function that performs search tasks.
    Updates progress data in Redis to enable progress monitoring.
    """
    total = len(collection_items)
    results = []
    for i, item in enumerate(collection_items):
        # Process item and append to results
        result = transfer_from_discogs([item], access_token)
        results.extend(result)

        # Update progress in Redis
        progress = {'current': i + 1, 'total': total}
        celery_redis_client.set(progress_key, json.dumps(progress))

    # Mark as finished
    celery_redis_client.set(progress_key, json.dumps(
        {'current': total, 'total': total, 'finished': True}))
    return results
