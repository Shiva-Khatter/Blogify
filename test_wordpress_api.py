import logging
import requests
from decouple import config
from airtable import Airtable
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import base64
import time

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_wordpress_api():
    try:
        # Load credentials from .env
        wordpress_url = config('WORDPRESS_API_URL') + "/posts"
        wordpress_username = config('WORDPRESS_USERNAME')
        wordpress_password = config('WORDPRESS_APP_PASSWORD')
        airtable_base_id = config('AIRTABLE_BASE_ID')
        airtable_table_name = 'Blog Posts'  # Hard-coded to match cron.py
        airtable_api_key = config('AIRTABLE_API_KEY')

        # Encode credentials for Basic Auth
        credentials = f"{wordpress_username}:{wordpress_password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode('utf-8')

        # Connect to Airtable
        logging.info("Loading Airtable credentials from .env file")
        airtable = Airtable(airtable_base_id, airtable_table_name, airtable_api_key)
        logging.info("Connected to Airtable")

        # Fetch scheduled posts from Airtable
        records = airtable.get_all(formula="FIND('Scheduled', {Status})")
        if not records:
            logging.info("No scheduled posts found in Airtable")
            print("No scheduled posts found in Airtable.")
            logging.info("Test failed. Check the logs for details.")
            print("Test failed. Check the logs for details.")
            return

        # Take the first scheduled post
        record = records[0]
        record_id = record['id']
        fields = record['fields']
        title = fields.get('Title', 'Test Post')
        content = fields.get('Content', 'This is a test post.')
        primary_keyword = fields.get('Primary Keyword', '')
        additional_keywords = fields.get('Additional Keywords', '')

        # Prepare focus keywords (comma-separated string)
        focus_keywords = primary_keyword
        if additional_keywords:
            focus_keywords = f"{primary_keyword}, {additional_keywords}"

        # Set up a session with retries for WordPress requests
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

        # Prepare WordPress API request
        post_data = {
            'title': title,
            'content': content,
            'status': 'draft',
            'meta': {
                'custom_focus_keywords': focus_keywords
            }
        }

        # Post to WordPress
        logging.info(f"Attempting to post to WordPress: {title}")
        response = session.post(wordpress_url, headers=wp_headers, json=post_data, timeout=60)

        if response.status_code == 201:
            wp_post_id = response.json().get('id')
            logging.info(f"Successfully posted to WordPress: Post ID {wp_post_id}")
            print(f"Successfully posted to WordPress: Post ID {wp_post_id}")
            print(f"Set custom meta field 'custom_focus_keywords' to: {focus_keywords}")

            # Update Airtable status to Published
            update_data = {
                'Status': 'Published',
                'WP Post ID': str(wp_post_id)
            }
            airtable.update(record_id, update_data)
            logging.info("Updated Airtable record to Published")
            print(f"Updated Airtable record {record_id}: Status set to Published, WP Post ID set to {wp_post_id}")
            time.sleep(2)
        else:
            logging.error(f"Failed to post to WordPress: {response.status_code} - {response.text}")
            print(f"Failed to post to WordPress: {response.status_code} - {response.text}")

    except Exception as e:
        logging.error(f"Test failed: {str(e)}")
        print(f"Test failed: {str(e)}")

if __name__ == "__main__":
    test_wordpress_api()