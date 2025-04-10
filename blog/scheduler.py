# blog/scheduler.py
from django.http import JsonResponse
import logging
from .cron import publish_scheduled_blogs  # Import the publishing function
from pyairtable import Table
from decouple import config
from datetime import datetime
import pytz

# Setting up logging to send messages to Vercel logs
logger = logging.getLogger(__name__)

def schedule_new_blogs():
    """
    Check Airtable for scheduled SEO blog posts and publish them to WordPress if their Publish Date has passed.
    This function will be called by the cron job.
    """
    # Configuring to Airtable
    api_key = config('AIRTABLE_API_KEY')
    base_id = config('AIRTABLE_BASE_ID')
    table_name = config('AIRTABLE_TABLE_NAME')
    table = Table(api_key, base_id, table_name)

    # Fetching all scheduled blog posts
    records = table.all(formula="{Status}='Scheduled'")
    if not records:
        logger.info("No scheduled SEO blog posts found in Airtable.")
        return

    for record in records:
        record_id = record['id']
        fields = record['fields']
        title = fields.get('Title', 'Untitled')
        publish_date_str = fields.get('Publish Date', '')

        if not publish_date_str:
            logger.info(f"Blog '{title}' has no Publish Date. Skipping.")
            continue

        try:
            # Parsing the Publish Date in ISO 8601 format (e.g., "2025-03-25T00:00:00.000Z")
            publish_date = datetime.strptime(publish_date_str, '%Y-%m-%dT%H:%M:%S.%fZ')
            publish_date = publish_date.replace(tzinfo=pytz.UTC)
            local_tz = pytz.timezone('Asia/Kolkata')  # Use IST timezone
            publish_date = publish_date.astimezone(local_tz)
            now = datetime.now(local_tz)

            logger.info(f"Checking blog '{title}' (Record ID: {record_id})")
            logger.info(f"Publish Date: {publish_date.strftime('%Y-%m-%d %I:%M%p %Z')}")
            logger.info(f"Current Time: {now.strftime('%Y-%m-%d %I:%M%p %Z')}")
            logger.info(f"Is Publish Date in the past? {publish_date <= now}")

            if publish_date <= now:
                logger.info(f"Publish Date for '{title}' is in the past ({publish_date_str}). Posting as draft to WordPress.")
                publish_scheduled_blogs(record_id=record_id, immediate=False)  # Post as draft
            else:
                logger.info(f"Blog '{title}' is scheduled for {publish_date.strftime('%Y-%m-%d %I:%M%p %Z')}. Waiting to publish.")
        except ValueError as e:
            logger.error(f"Invalid Publish Date format for '{title}': {publish_date_str}. Error: {str(e)}")
            continue

def run_scheduler(request):
    """
    Vercel cron job endpoint to trigger the scheduler.
    Returns a JSON response for Vercel compatibility.
    """
    logger.info("Scheduler cron job triggered.")
    schedule_new_blogs()
    logger.info("Scheduler run completed.")
    return JsonResponse({"status": "success", "message": "Scheduler executed"})
