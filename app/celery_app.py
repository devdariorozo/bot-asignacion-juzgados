from celery import Celery
from celery.schedules import crontab
import os
from dotenv import load_dotenv

load_dotenv()

#Redis
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = os.getenv('REDIS_PORT', '6379')
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"

#crear Celery
celery_app = Celery(
    'court_assignment_bot',
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=['app.tasks']
)

#configuración de Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='America/Bogota',
    enable_utc=False,
    task_track_started=True,
    task_time_limit=30 * 60,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)


#producción
celery_app.conf.beat_schedule = {
    'sync-and-assign-hourly-business-hours': {
        'task': 'app.tasks.scheduled_sync_and_assign',
        'schedule': crontab(
            minute=0,
            hour='7-22',
            day_of_week='mon-fri',
        ),
    },
    'reset-daily-api-counter': {
        'task': 'app.tasks.reset_daily_api_counter',
        'schedule': crontab(
            minute=0,
            hour=0,
        ),
    },
}


# celery_app.conf.beat_schedule = {
#     'sync-and-assign-every-hour-daytime': {
#         'task': 'app.tasks.scheduled_sync_and_assign',
#         'schedule': crontab(
#             minute=0,
#             hour='7-22',
#             day_of_week='mon-sun',
#         ),
#     },
#     # Resetear contador a medianoche
#     'reset-daily-api-counter': {
#         'task': 'app.tasks.reset_daily_api_counter',
#         'schedule': crontab(
#             minute=0,
#             hour=0,
#         ),
#     },
# }
