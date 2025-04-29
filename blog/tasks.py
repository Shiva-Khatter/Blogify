from celery import shared_task
from django.utils import timezone
from blog.models import ScheduledPost, Post
import google.generativeai as genai
import django
from celery.utils.log import get_task_logger

django.setup()
logger = get_task_logger(__name__)

genai.configure(api_key="AIzaSyDnQKVzA9vipdW_Idy3YJRmov95gCONsoM")  # Same key as in views.py

@shared_task
def process_scheduled_posts():
    now = timezone.now()
    scheduled_posts = ScheduledPost.objects.filter(
        scheduled_datetime__lte=now,
        created_by__is_superuser=True
    )
    for sp in scheduled_posts:
        logger.info(f"Processing scheduled post: {sp.topic}")
        # Generating the content directly
        prompt = (
            f"Write a 500-word blog post on '{sp.topic}'. Ensure the article uses the primary keyword '{sp.primary_keyword}' "
            f"5-10 times (1-2% density) for SEO. Include additional keywords '{sp.additional_keywords}' naturally."
        )
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            content = response.text
            logger.info(f"Generated content for: {sp.topic}")
        except Exception as e:
            logger.error(f"Failed to generate content for {sp.topic}: {str(e)}")
            continue

        # Extracting the title from content (like in publish action)
        lines = content.split('\n')
        title = sp.topic  # Default to topic
        for line in lines:
            if line.strip().startswith('#'):
                title = line.strip().replace('#', '').strip()
                break

        # Create and publish the Post
        post = Post(
            title=title,
            content=content,
            author=sp.created_by,
            seo_keywords=f"{sp.primary_keyword}, {sp.additional_keywords}",
            is_draft=False  # Published directly
        )
        post.save()
        logger.info(f"Published post: {title}")

        # Delete the ScheduledPost
        sp.delete()
        logger.info(f"Deleted scheduled post: {sp.topic}")