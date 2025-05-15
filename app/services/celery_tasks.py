import os

from celery import Celery

from .spotify import transfer_from_discogs

# Celery and Redis client configuration
celery = Celery(
    'discofy',
    broker=os.environ.get('REDIS_URL', 'redis://redis:6379'),
    backend=os.environ.get('REDIS_URL', 'redis://redis:6379')
)


@celery.task(bind=True)
def transfer_collection_task(self, collection_items, access_token, progress_key):
    return transfer_from_discogs(collection_items, access_token, progress_key)
