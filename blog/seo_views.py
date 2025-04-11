from django.shortcuts import render, redirect
from django.views.generic import View
from django.contrib.auth.mixins import LoginRequiredMixin
from blog.generate_seo_content import fetch_google_articles, extract_article_text, clean_text, generate_blog_content, save_to_airtable
from blog.cron import publish_scheduled_blogs
import google.generativeai as genai
from decouple import config
import requests
from datetime import datetime
import pytz  # For timezone handling

# Configuring Gemini API
genai.configure(api_key=config('GEMINI_API_KEY'))

class SEOBlogGeneratorView(LoginRequiredMixin, View):
    template_name = 'blog/seo_generator.html'
    login_url = '/login/'

    def get(self, request):
        keyword = request.session.get('keyword', '')
        draft = request.session.get('seo_draft', {})
        feedback = request.session.get('feedback', '')
        body = draft.get('body', '') if isinstance(draft.get('body', ''), str) else ''
        word_count = len(body.split()) if body else 0
        return render(request, self.template_name, {
            'keyword': keyword,
            'draft': draft.get('body', ''),
            'title': draft.get('title', ''),
            'word_count': word_count,
            'feedback': feedback,
            'grammar_result': request.session.get('grammar_result', ''),
            'error': request.session.get('error', ''),
        })

    def post(self, request):
        # Capturing the keyword from the form and preserve it
        initial_keyword = request.POST.get('keyword', '').strip()
        feedback = request.POST.get('feedback', '').strip()
        action = request.POST.get('action')
        draft = request.session.get('seo_draft', {})

        # Storing the initial keyword in the session and use it throughout
        request.session['keyword'] = initial_keyword if initial_keyword else request.session.get('keyword', '')
        keyword = request.session['keyword']  # Use session keyword consistently
        request.session['feedback'] = feedback
        request.session['error'] = ''

        # Debug: Logging the keyword at every stage
        print(f"Initial keyword from form: '{initial_keyword}'")
        print(f"Keyword stored in session: '{request.session['keyword']}'")
        print(f"Current keyword in use: '{keyword}'")

        if action == 'generate':
            if not keyword:
                request.session['error'] = "Please provide a keyword/topic."
            else:
                urls = fetch_google_articles(keyword, num_results=4)
                raw_texts = extract_article_text(urls)
                cleaned_texts = [clean_text(text) for text in raw_texts]
                blog_content = generate_blog_content(cleaned_texts, keyword)
                if not blog_content['body']:
                    request.session['error'] = "Failed to generate blog content."
                else:
                    draft = blog_content
                    # Preparing record for Airtable (optional: save draft to Airtable)
                    record = {
                        "Title": draft['title'],
                        "Content": draft['body'],
                        "SEO Summary": draft.get('meta_description', ''),
                        "Primary Keyword": keyword,
                        "Status": "Draft",  # Set as Draft since this is the initial generation
                        "Created At": datetime.now().isoformat()
                    }
                    print("Record being sent to Airtable (generate):", record)  # Debug
                    # save_to_airtable(record)
                    request.session['seo_draft'] = draft
                    request.session['grammar_result'] = ''
                    print("Draft after generation:", draft)

        elif action == 'refine':
            if not draft:
                request.session['error'] = "No draft to refine. Please generate a draft first."
            elif not feedback:
                request.session['error'] = "Please provide feedback to refine the draft."
            else:
                model = genai.GenerativeModel('gemini-1.5-flash')
                prompt = (
                    f"Refine this blog post: '{draft['body']}' based on the following feedback: '{feedback}'. "
                    f"Keep it SEO-optimized for the keyword '{keyword}' and maintain a similar length."
                )
                try:
                    response = model.generate_content(prompt)
                    draft['body'] = response.text.strip()
                    request.session['seo_draft'] = draft
                    request.session['grammar_result'] = ''
                    print("Draft after refinement:", draft)
                except Exception as e:
                    request.session['error'] = f"Error refining blog: {str(e)}"

        elif action == 'humanize':
            if not draft:
                request.session['error'] = "No draft to humanize. Please generate a draft first."
            else:
                original_body = draft['body']
                original_word_count = len(original_body.split()) if original_body else 0
                print("Original word count before humanizing:", original_word_count)

                model = genai.GenerativeModel('gemini-1.5-flash')
                min_words = max(0, original_word_count - 30)
                max_words = original_word_count + 30
                prompt = (
                    f"Rewrite this blog post: '{draft['body']}' to sound less robotic, with a natural, conversational tone and a flowy structure. "
                    f"Preserve all HTML tags (<h2>, <p>, <strong>, <em>) as they are essential for WordPress formatting. "
                    f"Remove any special characters like **, ##, or other markdown formatting that are not HTML. "
                    f"Maintain SEO optimization for the keyword '{keyword}'. "
                    f"The original blog has {original_word_count} words. Ensure the rewritten blog has a word count between {min_words} and {max_words} words, "
                    f"avoiding any significant decrease in length. If necessary, add relevant details or examples to maintain the length while improving the tone."
                )
                try:
                    response = model.generate_content(prompt)
                    draft['body'] = response.text.strip()
                    request.session['seo_draft'] = draft
                    new_word_count = len(draft['body'].split()) if draft['body'] else 0
                    word_count_diff = new_word_count - original_word_count
                    print("New word count after humanizing:", new_word_count)
                    print("Word count difference (new - original):", word_count_diff)
                    print("Draft after humanizing:", draft)
                except Exception as e:
                    request.session['error'] = f"Error humanizing blog: {str(e)}"

        elif action == 'check_grammar':
            if not draft:
                request.session['error'] = "No draft to check. Please generate a draft first."
            else:
                url = "https://api.languagetool.org/v2/check"
                data = {'text': draft['body'], 'language': 'en-US'}
                try:
                    response = requests.post(url, data=data)
                    result = response.json()
                    matches = result.get('matches', [])
                    if matches:
                        fixed_text = draft['body']
                        offset_shift = 0
                        for match in matches:
                            # Skipping the fixes that might affect the HTML Tags 
                            if any(fixed_text[match['offset'] + offset_shift:match['offset'] + offset_shift + match['length']].startswith(tag) 
                                   for tag in ['<h2>', '<p>', '<strong>', '<em>', '</h2>', '</p>', '</strong>', '</em>']):
                                continue
                            start = match['offset'] + offset_shift
                            length = match['length']
                            replacement = match['replacements'][0]['value'] if match['replacements'] else fixed_text[start:start+length]
                            fixed_text = fixed_text[:start] + replacement + fixed_text[start+length:]
                            offset_shift += len(replacement) - length
                        draft['body'] = fixed_text
                        request.session['grammar_result'] = f"Applied {len(matches)} grammar fixes (HTML tags preserved)."
                    else:
                        request.session['grammar_result'] = "No grammar issues found."
                    request.session['seo_draft'] = draft
                    print("Draft after grammar check:", draft)
                except Exception as e:
                    request.session['error'] = f"Grammar check failed: {str(e)}"

        elif action in ['schedule', 'publish']:
            if not draft:
                request.session['error'] = "No draft to schedule or publish."
            else:
                publish_date_str = request.POST.get('publish_date')
                if not publish_date_str and action == 'schedule':
                    request.session['error'] = "Please provide a publish date for scheduling."
                else:
                    try:
                        # Defining the timezone (IST, since your server time is in +0530)
                        local_tz = pytz.timezone('Asia/Kolkata')

                        # Parsing the publish date or use current time for immediate publishing
                        if publish_date_str:
                            publish_date = datetime.strptime(publish_date_str, "%Y-%m-%dT%H:%M")
                            publish_date = local_tz.localize(publish_date)  # Make publish_date timezone-aware
                        else:
                            publish_date = datetime.now(local_tz)  # Use current time for "Publish Now"

                        # Current time in the same timezone
                        now = datetime.now(local_tz)

                        # Debug: Logging the dates
                        print(f"Action: {action}")
                        print(f"Publish Date (parsed): {publish_date}")
                        print(f"Current Time: {now}")

                        # Debug: Logging the keyword before preparing the record
                        print(f"Keyword before preparing record: '{keyword}'")
                        print(f"Session keyword: '{request.session.get('keyword', '')}'")

                        # Determining status based on the action
                        if action == 'schedule':
                            status = "Scheduled"
                        else:  # action == 'publish'
                            status = "Published"
                        print(f"Determined Status: {status}")

                        # Preparing record for Airtable with ensured Primary Keyword
                        record = {
                            "Title": draft['title'],
                            "Content": draft['body'],
                            "SEO Summary": draft.get('meta_description', ''),
                            "Primary Keyword": keyword if keyword else request.session.get('keyword', 'N/A'),  # Enforce keyword
                            "Publish Date": publish_date.isoformat(),
                            "Status": status,
                            "Created At": datetime.now().isoformat()
                        }
                        print("Record being sent to Airtable:", record)  # Debug: Log the record
                        # Saving to Airtable using full record
                        saved_record = save_to_airtable(record)
                        if saved_record:
                            if status == "Published":
                                print("Status is Published, calling publish_scheduled_blogs() to publish immediately")
                                # Passing the record_id from the saved record, indicate immediate publishing
                                publish_scheduled_blogs(record_id=saved_record['id'], immediate=True)
                            else:
                                print("Status is Scheduled, not publishing immediately")
                            # Clearing session to reset the form
                            request.session['seo_draft'] = {}
                            request.session['keyword'] = ''
                            request.session['feedback'] = ''
                            request.session['grammar_result'] = ''
                            request.session.modified = True
                            return redirect('blog-home')  # Redirect to homepage after success
                        else:
                            request.session['error'] = "Failed to save to Airtable."
                    except ValueError as e:
                        request.session['error'] = f"Invalid date format. Use YYYY-MM-DDTHH:MM. Error: {str(e)}"

        body = draft.get('body', '') if isinstance(draft.get('body', ''), str) else ''
        word_count = len(body.split()) if body else 0
        print("Word count in POST:", word_count)
        request.session.modified = True
        return render(request, self.template_name, {
            'keyword': keyword,
            'draft': draft.get('body', ''),
            'title': draft.get('title', ''),
            'word_count': word_count,
            'feedback': feedback,
            'grammar_result': request.session.get('grammar_result', ''),
            'error': request.session.get('error', ''),
        })