# cron.py
import requests
from decouple import config
from datetime import datetime
import pytz
import base64
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time

def publish_scheduled_blogs(record_id=None, immediate=False):
    """
    Publish a blog post to WordPress and update its Airtable record.
    Args:
        record_id (str, optional): The Airtable record ID of the blog post to publish.
                                   If None and immediate=True, fetch the most recent "Published" post.
        immediate (bool): If True, publish immediately to WordPress with status "publish".
                          If False, post as a draft (for scheduled blogs).
    """
    print(f"Cron job running: Checking for blogs to publish (record_id: {record_id}, immediate: {immediate})...")

    # Airtable configuration
    airtable_api_key = config('AIRTABLE_API_KEY')
    airtable_base_id = config('AIRTABLE_BASE_ID')
    airtable_table_name = 'Blog Posts'
    airtable_url = f"https://api.airtable.com/v0/{airtable_base_id}/{airtable_table_name}"

    # WordPress configuration
    wordpress_url = config('WORDPRESS_API_URL') + "/posts"
    wordpress_username = config('WORDPRESS_USERNAME')
    wordpress_password = config('WORDPRESS_APP_PASSWORD')

    # Encoding the credentials for Basic Auth
    credentials = f"{wordpress_username}:{wordpress_password}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode('utf-8')

    # Headers for Airtable API
    headers = {
        'Authorization': f'Bearer {airtable_api_key}',
        'Content-Type': 'application/json'
    }

    # Fetching the specific record if record_id is provided, otherwise fetch all scheduled records
    if record_id:
        try:
            response = requests.get(f"{airtable_url}/{record_id}", headers=headers)
            response.raise_for_status()
            record = response.json()
            records = [record] if record else []
            print(f"Fetched specific record {record_id} from Airtable.")
        except Exception as e:
            print(f"Error fetching record {record_id} from Airtable: {str(e)}")
            return
    else:
        if immediate:
            # Fetching  most recent "Published" record for immediate publishing
            params = {
                'filterByFormula': '{Status} = "Published"',
                'sort[0][field]': 'Created At',
                'sort[0][direction]': 'desc',
                'maxRecords': 1
            }
        else:
            # Fetching all scheduled records whose Publish Date has passed
            params = {
                'filterByFormula': 'AND({Status} = "Scheduled", {Publish Date} <= NOW())',
                'sort[0][field]': 'Publish Date',
                'sort[0][direction]': 'asc'
            }
        try:
            response = requests.get(airtable_url, headers=headers, params=params)
            response.raise_for_status()
            records = response.json().get('records', [])
            print(f"Found {len(records)} blogs to publish (immediate={immediate}).")
            # Debug: Print the status of each fetched record
            for record in records:
                record_id = record['id']
                status = record['fields'].get('Status', 'Unknown')
                print(f"Record {record_id}: Status = {status}")
        except Exception as e:
            print(f"Error fetching records from Airtable: {str(e)}")
            return

    if not records:
        print("No blog posts to publish.")
        return

    # Setting up a session with retries for WordPress requests
    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504, 406],
        allowed_methods=["POST", "PUT"]
    )
    session.mount('https://', HTTPAdapter(max_retries=retries))

    # WordPress headers
    wp_headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': f"Basic {encoded_credentials}",
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
        'Referer': config('WORDPRESS_API_URL').rstrip('/wp-json/wp/v2')
    }

    # Processing each record
    for record in records:
        record_id = record['id']
        fields = record['fields']
        title = fields.get('Title', '')
        content = fields.get('Content', '')
        primary_keyword = fields.get('Primary Keyword', '')
        additional_keywords = fields.get('Additional Keywords', '')
        status = fields.get('Status', 'Unknown')

        # Determine expected status based on immediate parameter
        expected_status = "Published" if immediate else "Scheduled"
        # Skip if the record is not in the correct status
        if status != expected_status:
            print(f"Skipping record {record_id}: Status is '{status}', expected '{expected_status}'.")
            continue

        # Skipping if the record already has a WP Post ID (to prevent duplicates)
        if fields.get('WP Post ID'):
            print(f"Skipping record {record_id}: Already published with WP Post ID {fields.get('WP Post ID')}")
            continue

        # Preparing focus keywords (comma-separated string)
        focus_keywords = primary_keyword
        if additional_keywords:
            focus_keywords = f"{primary_keyword}, {additional_keywords}"

        # Determining the WordPress post status
        wp_status = "publish" if immediate else "draft"
        print(f"Posting to WordPress with status: {wp_status}")

        # Posting to WordPress with the appropriate status and custom meta field
        wp_data = {
            'title': title,
            'content': content,
            'status': wp_status,
            'meta': {
                'custom_focus_keywords': focus_keywords
            }
        }
        try:
            wp_response = session.post(wordpress_url, headers=wp_headers, json=wp_data, timeout=60)
            wp_response.raise_for_status()
            wp_post_id = wp_response.json().get('id')
            action = "published" if immediate else "saved as draft"
            print(f"Successfully {action} in WordPress: {title}, Post ID: {wp_post_id}")
            print(f"Set custom meta field 'custom_focus_keywords' to: {focus_keywords}")
        except Exception as e:
            print(f"Error posting to WordPress for record {record_id}: {str(e)}")
            print(f"WordPress response: {e.response.text if e.response else 'No response'}")
            continue

        # Updating Airtable with Status and WP Post ID
        new_status = "Published"  # Using "Published" for both immediate and scheduled posts
        update_data = {
            'fields': {
                'Status': new_status,  # Ensuring this matches the exact case in Airtable
                'WP Post ID': str(wp_post_id)
            }
        }
        try:
            update_response = requests.patch(f"{airtable_url}/{record_id}", headers=headers, json=update_data)
            update_response.raise_for_status()
            print(f"Updated Airtable record {record_id}: Status set to {new_status}, WP Post ID set to {wp_post_id}")
            time.sleep(2)
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error updating Airtable for record {record_id}: {str(http_err)}")
            print(f"Airtable status code: {update_response.status_code}")
            print(f"Airtable response: {update_response.text}")
            print(f"Request payload: {update_data}")
            # If the error is due to an invalid then selecting option, log a suggestion
            if update_response.status_code == 422 and "INVALID_MULTIPLE_CHOICE_OPTIONS" in update_response.text:
                print(f"Suggestion: Check the 'Status' field options in Airtable. Ensure '{new_status}' is an allowed option (case-sensitive).")
            continue
        except Exception as e:
            print(f"Unexpected error updating Airtable for record {record_id}: {str(e)}")
            continue
# must create a different cron job onto vercel for scheduler to work (Celery and AP wont in a production environment )