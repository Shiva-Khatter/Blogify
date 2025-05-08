# Blogify: Django Blog Scheduler

## Overview
Blogify is a Django-based application designed to automate the process of scheduling and publishing blog posts from Airtable to a WordPress site. It uses a cron job to periodically fetch scheduled posts from Airtable and publish them as drafts to WordPress via the REST API. The project includes a test script for manual API testing and demonstrates skills in Django, API integration, task scheduling, and error handling.

## Features


### Django Backend Core
- **Cron Job Scheduling**: A custom management command (`start_scheduler`) uses `django-apscheduler` to run a cron job that checks Airtable for scheduled posts every minute.
- **Airtable Integration**: Fetches blog posts from Airtable based on their status (e.g., "Scheduled") and publish date.
- **WordPress Integration**: Publishes posts as drafts to WordPress using the REST API, including custom meta fields like focus keywords.
- **Status Updates**: Updates Airtable records with the WordPress post ID and status (e.g., "Published") after successful publishing.
- **Error Handling**: Implements retry logic for API requests to handle network issues or rate limits.
- **Configuration Management**: Uses `python-decouple` to securely store sensitive data (e.g., API keys, WordPress URL) in a `.env` file.
- **Database**: Uses SQLite (Django’s default) for lightweight storage of scheduler data.

### API Testing
- **Manual Testing Script**: Includes `test_wordpress_api.py` to manually test the WordPress API integration by posting a sample blog post.
- **Debugging**: Logs API responses and errors for easy troubleshooting.

### Security
- **Sensitive Data Protection**: API keys, WordPress credentials, and other sensitive information are stored in a `.env` file, which is excluded from version control via `.gitignore`.

## Tech Stack

### Backend
- **Django 5.1.1 (Python 3.12)**: Web framework for building the application and management commands.
- **Models**: Uses Django’s ORM for database interactions (e.g., `apscheduler` tables).
- **Management Commands**: Custom command (`start_scheduler`) to run the scheduler.

### APIs and Libraries
- **Airtable API**: Fetches blog post data using the `airtable-python-wrapper` library.
- **WordPress REST API**: Publishes blog posts with custom meta fields using the `requests` library.
- **Python Libraries**:
  - `requests`: For making HTTP requests to Airtable and WordPress APIs.
  - `python-decouple`: For managing environment variables.
  - `django-apscheduler`: For scheduling the cron job.
  - `airtable-python-wrapper`: For interacting with the Airtable API.
  

### Database
- **SQLite**: Django’s default database, used for storing scheduler data.

## Setup Instructions
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/Shiva-Khatter/Blogify.git
   cd Blogify
