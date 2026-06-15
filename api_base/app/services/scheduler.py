import asyncio
import logging

from app.models.base_db import (
    get_pending_scheduled,
    mark_scheduled_sent,
    create_notification,
    create_notification_broadcast,
    get_user_by_username,
)

logger = logging.getLogger(__name__)

_task = None

async def _check_scheduled_notifications():
    """Background loop: check and send scheduled notifications every 60s."""
    while True:
        try:
            pending = get_pending_scheduled()
            for item in pending:
                target = item.get('target', 'all')
                title = item['title']
                message = item['message']
                ntype = item.get('type', 'info')

                if target == 'all':
                    count = create_notification_broadcast(title, message, ntype)
                    logger.info(f"Scheduled notification #{item['id']} sent to {count} users")
                else:
                    user = get_user_by_username(target)
                    if user:
                        create_notification(user['id'], title, message, ntype)
                        logger.info(f"Scheduled notification #{item['id']} sent to user '{target}'")
                    else:
                        logger.warning(f"Scheduled notification #{item['id']}: user '{target}' not found")

                mark_scheduled_sent(item['id'])
        except Exception as e:
            logger.error(f"Scheduler error: {e}")

        await asyncio.sleep(60)


def start_scheduler():
    """Start the background scheduler task."""
    global _task
    if _task is None or _task.done():
        _task = asyncio.create_task(_check_scheduled_notifications())
        logger.info("Notification scheduler started.")
