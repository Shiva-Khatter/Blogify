import requests
from decouple import config
from bs4 import BeautifulSoup
import re
import google.generativeai as genai
from pyairtable import Table
from datetime import datetime

def fetch_google_articles(primary_keyword, num_results=4, fetch_limit=10):
    """
    Fetch top articles from Google using the Custom Search API, filtering out ads and social media.
    Args:
        primary_keyword (str): The primary keyword to search for (e.g., "best hiking boots").
        num_results (int): Number of organic articles to return (default: 4).
        fetch_limit (int): Number of results to fetch before filtering (default: 10).
    Returns:
        list: List of organic article URLs.
    """
    api_key = config('GOOGLE_API_KEY')
    cx = config('GOOGLE_CX')
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        'key': api_key,
        'cx': cx,
        'q': primary_keyword,
        'num': fetch_limit,
        'safe': 'active',  # for safe search to filter out any spam/ads/fraudulent content on the web
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        results = response.json().get('items', [])
        
        organic_results = []
        ad_domains = ['googleads.g.doubleclick.net', 'adservice.google.com']  # common ad domains (to be ignored)
        social_media_domains = ['reddit.com', 'instagram.com', 'facebook.com']
        for item in results:
            display_link = item.get('displayLink', '')
            if any(ad_domain in display_link for ad_domain in ad_domains):
                print(f"Skipping ad: {display_link}")
                continue
            if any(social_domain in display_link for social_domain in social_media_domains):
                print(f"Skipping social media: {display_link}")
                continue
            organic_results.append(item['link'])
        
        return organic_results[:num_results]
    except requests.exceptions.RequestException as e:
        print(f"Error fetching Google articles: {str(e)}")
        return []

def extract_article_text(article_urls):
    """
    Extract text from a list of article URLs using requests and BeautifulSoup.
    Args:
        article_urls (list): List of article URLs to scrape.
    Returns:
        list: List of extracted text content (one per URL).
    """
    if not article_urls:
        print("No URLs provided for extraction.")
        return []

    extracted_texts = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    for url in article_urls:
        if not url:
            print("Skipping empty URL.")
            continue
        
        try:
            print(f"Scraping URL with BeautifulSoup: {url}")
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            article = None
            selectors = [
                'article',
                '.article-content',
                '.post-content',
                '.entry-content',
                'main',
                '.content'
            ]
            for selector in selectors:
                element = soup.select_one(selector)
                if element:
                    article = element.get_text(strip=True)
                    break
            
            if not article:
                article = soup.body.get_text(strip=True) if soup.body else ""
            
            if article:
                extracted_texts.append(article)
                print(f"Successfully extracted text for URL: {url} (Length: {len(article)} characters)")
            else:
                print(f"No text extracted for URL: {url}")
        except requests.exceptions.RequestException as e:
            print(f"Error scraping URL {url}: {str(e)}")
            continue
    
    return extracted_texts

def clean_text(text):
    """
    Clean the extracted text by removing personal info, contact info, emojis, and irrelevant content.
    Args:
        text (str): The raw extracted text.
    Returns:
        str: The cleaned text.
    """
    if not text:
        return ""

    # Removing personal info (e.g., author names, "Post author: Sakshi Padiyar")
    text = re.sub(r'Post author:\s*[A-Za-z\s]+', '', text, flags=re.IGNORECASE)
    text = re.sub(r'Comment by\s*[A-Za-z\s]+', '', text, flags=re.IGNORECASE)
    text = re.sub(r'Author\s*-\s*[A-Za-z\s]+', '', text, flags=re.IGNORECASE)

    # Removing metadata (e.g., "Post published:Oct 1, 2022", "LAST UPDATED: 26/02/25")
    text = re.sub(r'Post published:\s*[A-Za-z0-9\s,]+', '', text, flags=re.IGNORECASE)
    text = re.sub(r'Post last modified:\s*[A-Za-z0-9\s,]+', '', text, flags=re.IGNORECASE)
    text = re.sub(r'LAST UPDATED:\s*[0-9/]+', '', text, flags=re.IGNORECASE)
    text = re.sub(r'updated on\s*[0-9T:.-Z]+', '', text, flags=re.IGNORECASE)
    text = re.sub(r':school/Blog', '', text, flags=re.IGNORECASE)
    text = re.sub(r':Mar 26, 2025The Top 10 Boarding Schools in Dehradun for 2025-26', '', text, flags=re.IGNORECASE)
    text = re.sub(r'The Top 10 Boarding Schools in Dehradun for 2025-26', '', text, flags=re.IGNORECASE)

    # Removing email addresses
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '', text)

    # Removing phone numbers (e.g., +91 1234567890, (123) 456-7890)
    text = re.sub(r'\+?\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', '', text)

    # Removing addresses (simplified, looks for patterns like "123 Street Name, City, State")
    text = re.sub(r'\d+\s+[A-Za-z\s]+,\s*[A-Za-z\s]+,\s*[A-Za-z\s]+,\s*India\s*\d{6}', '', text, flags=re.IGNORECASE)
    text = re.sub(r'[A-Za-z\s]+,\s*[A-Za-z\s]+,\s*Uttarakhand,\s*India\s*\d{5,6}', '', text, flags=re.IGNORECASE)

    # Removing emojis (Unicode range for emojis)
    text = re.sub(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]', '', text)

    # Removing navigation/menu-related text
    text = re.sub(r'Enquire now|Table of Contents|Toggle|Read More|Leave a Reply|Cancel reply|Enter your name or username to comment|Enter your email address to comment|Enter your website URL \(optional\)|Save my name, email, and website in this browser for the next time I comment|Also Read:.*?(?=\n|$)', '', text, flags=re.IGNORECASE)

    # Removing comments section (e.g., "This Post Has 40 Comments" and everything after)
    text = re.split(r'This Post Has \d+ Comments', text, flags=re.IGNORECASE)[0]

    # Removing ratings (e.g., "4.5 ⭐⭐⭐⭐⭐ (619 Reviews)")
    text = re.sub(r'\d\.\d\s*⭐+\s*\(\d+\s*Reviews\)', '', text)

    # Removing specific school info (e.g., "Fee Structure (Annual)Rs 700000 – 1000000", "Grades4-12")
    text = re.sub(r'Fee Structure \(Annual\)Rs \d+(?:\s*–\s*\d+)?', '', text)
    text = re.sub(r'Grades(KG|[0-9]+)-[0-9]+', '', text)
    text = re.sub(r'Indoor (Sports|Games)\w+[^:\n]*(?=\n|$)', '', text)
    text = re.sub(r'Outdoor sports\w+[^:\n]*(?=\n|$)', '', text)

    # Removing section headers (e.g., "Important School Information:-", "Location –")
    text = re.sub(r'Important School Information:-|Location\s*–|Address', '', text, flags=re.IGNORECASE)

    # Removing extra whitespace and newlines
    text = re.sub(r'\s+', ' ', text).strip()

    return text

def generate_description(texts, primary_keyword):
    """
    Generate a description of the extracted texts using Gemini Flash 1.5.
    Args:
        texts (list): List of cleaned extracted texts.
        primary_keyword (str): The primary keyword to focus the description on.
    Returns:
        str: The generated description.
    """
    if not texts:
        print("No texts provided for description generation.")
        return ""

    combined_text = " ".join(texts)
    if not combined_text:
        print("Combined text is empty after cleaning.")
        return ""

    gemini_api_key = config('GEMINI_API_KEY')
    genai.configure(api_key=gemini_api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

    prompt = f"""
    Summarize the following text into a concise meta description (150-160 characters) focusing on the main content related to '{primary_keyword}'. 
    Ensure the description is SEO-optimized by including the keyword '{primary_keyword}' at least once, ideally near the beginning.
    Exclude any personal information, contact details, or irrelevant metadata. Focus on the core information about the topic.

    Text: {combined_text}

    Provide a professional meta description suitable for a blog post.
    """

    try:
        print("Generating description with Gemini...")
        response = model.generate_content(prompt)
        description = response.text.strip()
        # Ensure the description is within 150-160 characters
        if len(description) > 160:
            description = description[:157] + "..."
        print(f"Generated meta description (Length: {len(description)} characters): {description}")
        return description
    except Exception as e:
        print(f"Error generating description with Gemini: {str(e)}")
        return f"Discover insights on {primary_keyword} in this detailed guide."

def generate_blog_content(texts, primary_keyword):
    """
    Generate a blog post (title, meta description, body) using the cleaned texts with Gemini Flash 1.5.
    Args:
        texts (list): List of cleaned extracted texts.
        primary_keyword (str): The primary keyword to focus the blog on.
    Returns:
        dict: A dictionary containing the title, meta description, and body of the blog.
    """
    if not texts:
        print("No texts provided for blog generation.")
        return {"title": "", "meta_description": "", "body": ""}

    combined_text = " ".join(texts)
    if not combined_text:
        print("Combined text is empty after cleaning.")
        return {"title": "", "meta_description": "", "body": ""}

    meta_description = generate_description(texts, primary_keyword)
    if not meta_description:
        meta_description = f"Discover insights on {primary_keyword} in this detailed guide."

    gemini_api_key = config('GEMINI_API_KEY')
    genai.configure(api_key=gemini_api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

    prompt = f"""
    Create a blog post about '{primary_keyword}' using the text below. The post should be in HTML format, optimized for WordPress, with:
    - A catchy title (up to 60 characters) including '{primary_keyword}'.
    - A body (800-1200 words, minimum 500 words) with an introduction, sections with <h2> subheadings, paragraphs in <p> tags, and emphasis with <strong> or <em>.
    - SEO-optimized, using '{primary_keyword}' 5-7 times, including in one <h2> and the intro/conclusion.
    - Focus only on the provided text, avoiding extra details.

    Text: {combined_text}

    Return the result as:
    Title: [Your title here]
    Body: [Your full HTML content here, e.g., <h2>Introduction</h2><p>Text...</p><h2>{primary_keyword} Section</h2><p>More text...</p>]
    """

    try:
        print("Generating blog content with Gemini...")
        response = model.generate_content(prompt)
        blog_content = response.text.strip()
        print(f"Raw Gemini response: {blog_content}")  # Debug: Log raw response

        title_match = re.search(r'Title:\s*(.+?)(?=\nBody:|\n|$)', blog_content, re.DOTALL)
        body_match = re.search(r'Body:\s*(.+)', blog_content, re.DOTALL)

        title = title_match.group(1).strip() if title_match else f"{primary_keyword}: A Comprehensive Guide"
        body = body_match.group(1).strip() if body_match else "No content generated."

        # Debug: Log extracted body
        print(f"Extracted body (raw): {body}")

        # Ensure body meets minimum length with fallback
        if len(body) < 800 and "No content generated" in body:
            body = f"<h2>Introduction to {primary_keyword}</h2><p>This is a fallback to ensure content. Please check input data or Gemini response.</p>"

        print(f"Generated blog title: {title}")
        print(f"Generated blog body (Length: {len(body)} characters): {body[:500]}...")

        return {
            "title": title,
            "meta_description": meta_description,
            "body": body
        }
    except Exception as e:
        print(f"Error generating blog content with Gemini: {str(e)}")
        return {"title": "", "meta_description": "", "body": ""}

def save_to_airtable(record):
    """
    Save the generated blog content to Airtable.
    Args:
        record (dict): Dictionary containing the fields to save to Airtable (e.g., Title, Content, Primary Keyword, etc.).
    Returns:
        dict or None: The saved record (including the 'id') if successful, None otherwise.
    """
    if not record.get("Title") or not record.get("Content"):
        print("No blog content to save to Airtable.")
        return None

    try:
        # Configure Airtable
        api_key = config('AIRTABLE_API_KEY')
        base_id = config('AIRTABLE_BASE_ID')
        table_name = config('AIRTABLE_TABLE_NAME')

        # Connect to the Airtable table
        table = Table(api_key, base_id, table_name)

        # Prepare the record to save
        airtable_record = {
            "Title": record.get("Title", ""),
            "Content": record.get("Content", ""),
            "SEO Summary": record.get("SEO Summary", ""),
            "Primary Keyword": record.get("Primary Keyword", ""),
            "Status": record.get("Status", "Draft"),
            "Publish Date": record.get("Publish Date", ""),
            "Created At": record.get("Created At", datetime.now().isoformat())
        }

        # Save the record to Airtable and return the saved record
        saved_record = table.create(airtable_record)
        print(f"Successfully saved blog post '{record.get('Title')}' to Airtable. Record ID: {saved_record['id']}")
        return saved_record

    except Exception as e:
        print(f"Error saving to Airtable: {str(e)}")
        return None

if __name__ == "__main__":
    primary_keyword = "Best Boarding schools in Deheradun"
    urls = fetch_google_articles(primary_keyword, num_results=4)
    print("Fetched URLs:", urls)
    raw_texts = extract_article_text(urls)
    print("Raw Extracted Texts:", raw_texts)
    
    cleaned_texts = [clean_text(text) for text in raw_texts]
    print("Cleaned Texts:", cleaned_texts)
    
    blog_content = generate_blog_content(cleaned_texts, primary_keyword)
    print("Blog Title:", blog_content["title"])
    print("Meta Description:", blog_content["meta_description"])
    print("Blog Body:", blog_content["body"])
    
    # Saving the blog content to Airtable
    record = {
        "Title": blog_content["title"],
        "Content": blog_content["body"],
        "SEO Summary": blog_content["meta_description"],
        "Primary Keyword": primary_keyword,
        "Status": "Draft",
        "Created At": datetime.now().isoformat()
    }
    saved_record = save_to_airtable(record)
    if saved_record:
        print("Blog content successfully saved to Airtable!")
    else:
        print("Failed to save blog content to Airtable.")