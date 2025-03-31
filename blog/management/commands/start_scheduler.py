from django.core.management.base import BaseCommand
from django_apscheduler.jobstores import DjangoJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from blog.cron import publish_scheduled_blogs

class Command(BaseCommand):
    help = 'Starts the APScheduler to run periodic tasks'

    def handle(self, *args, **options):
        scheduler = BackgroundScheduler()
        scheduler.add_jobstore(DjangoJobStore(), "default")

        # Scheduling the publish_scheduled_blogs function to run every minute
        scheduler.add_job(
            publish_scheduled_blogs,
            trigger=CronTrigger(minute="*/1"),  # Runs every minute
            id="publish_scheduled_blogs",
            max_instances=1,
            replace_existing=True,
        )

        scheduler.start()
        self.stdout.write(self.style.SUCCESS("Scheduler started successfully."))

        # Keeping this command running
        import time
        try:
            while True:
                time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            scheduler.shutdown()
            self.stdout.write(self.style.SUCCESS("Scheduler shut down successfully."))
            