import requests
import base64
from dotenv import load_dotenv
import os

# Loading the environment variables from .env file
load_dotenv()

# Getting credentials and URL from environment variables
wordpress_url = os.getenv("WORDPRESS_API_URL") + "/posts/764?context=edit"
wordpress_username = os.getenv("WORDPRESS_USERNAME")
wordpress_password = os.getenv("WORDPRESS_APP_PASSWORD")

credentials = f"{wordpress_username}:{wordpress_password}"
encoded_credentials = base64.b64encode(credentials.encode()).decode('utf-8')

headers = {
    'Authorization': f"Basic {encoded_credentials}",
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
}

response = requests.get(wordpress_url, headers=headers)
print(response.json().get('meta', {}))