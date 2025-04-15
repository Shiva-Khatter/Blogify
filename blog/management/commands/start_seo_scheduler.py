from django.core.management.base import BaseCommand
from blog.cron import publish_scheduled_blogs
from pyairtable import Table
from decouple import config
from datetime import datetime
import pytz
import time

def schedule_new_blogs(stdout):
    """Check for scheduled SEO blog posts and publish them as drafts to WordPress if their Publish Date has passed."""
    # Configure Airtable
    api_key = config('AIRTABLE_API_KEY')
    base_id = config('AIRTABLE_BASE_ID')
    table_name = config('AIRTABLE_TABLE_NAME')
    table = Table(api_key, base_id, table_name)

    # Fetch all scheduled blog posts
    records = table.all(formula="{Status}='Scheduled'")
    if not records:
        stdout.write("No scheduled SEO blog posts found in Airtable.")
        return

    for record in records:
        record_id = record['id']
        fields = record['fields']
        title = fields.get('Title', 'Untitled')
        publish_date_str = fields.get('Publish Date', '')

        if not publish_date_str:
            stdout.write(f"Blog '{title}' has no Publish Date. Skipping.")
            continue

        try:
            # Parse the Publish Date in ISO 8601 format (e.g., "2025-03-25T00:00:00.000Z")
            publish_date = datetime.strptime(publish_date_str, '%Y-%m-%dT%H:%M:%S.%fZ')
            # Convert to UTC timezone (since the 'Z' indicates UTC)
            publish_date = publish_date.replace(tzinfo=pytz.UTC)
            # Convert to local timezone (IST) for comparison with datetime.now()
            local_tz = pytz.timezone('Asia/Kolkata')  # Use IST timezone
            publish_date = publish_date.astimezone(local_tz)
            now = datetime.now(local_tz)

            # Debugging: Log the dates
            stdout.write(f"Checking blog '{title}' (Record ID: {record_id})")
            stdout.write(f"Publish Date: {publish_date.strftime('%Y-%m-%d %I:%M%p %Z')}")
            stdout.write(f"Current Time: {now.strftime('%Y-%m-%d %I:%M%p %Z')}")
            stdout.write(f"Is Publish Date in the past? {publish_date <= now}")

            if publish_date <= now:
                stdout.write(f"Publish Date for '{title}' is in the past ({publish_date_str}). Posting as draft to WordPress.")
                publish_scheduled_blogs(record_id=record_id, immediate=False)  # Post as draft
            else:
                stdout.write(f"Blog '{title}' is scheduled for {publish_date.strftime('%Y-%m-%d %I:%M%p %Z')}. Waiting to publish.")
        except ValueError as e:
            stdout.write(f"Invalid Publish Date format for '{title}': {publish_date_str}. Error: {str(e)}")
            continue

class Command(BaseCommand):
    help = 'Runs a periodic task to check and publish scheduled SEO blogs'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("SEO Scheduler started successfully."))

        # Periodically check for scheduled blog posts every 5 minutes
        try:
            while True:
                schedule_new_blogs(self.stdout)
                time.sleep(300)  # Sleep for 5 minutes (300 seconds)
        except (KeyboardInterrupt, SystemExit):
            self.stdout.write(self.style.SUCCESS("SEO Scheduler shut down successfully."))