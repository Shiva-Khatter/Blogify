from django.shortcuts import render, redirect
from django.views.generic import View
from blog.models import Post
from django.contrib.auth.mixins import LoginRequiredMixin
import google.generativeai as genai
from decouple import config
import requests
import json
from datetime import datetime

genai.configure(api_key=config('GEMINI_API_KEY'))

class BlogCraftView(LoginRequiredMixin, View):
    template_name = 'blog/blogcraft.html'
    login_url = '/login/'

    def get(self, request, *args, **kwargs):
        print("GET: Clearing session data")
        drafts = request.session.get('prompt_tier_drafts', [])
        current_refine_step = request.session.get('current_refine_step', 1)
        return render(request, self.template_name, {
            'topic': request.session.get('topic', ''),
            'primary_keyword': request.session.get('primary_keyword', ''),
            'additional_keywords': request.session.get('additional_keywords', ''),
            'prompt_1': request.session.get('prompt_1', ''),
            'prompt_2': request.session.get('prompt_2', ''),
            'prompt_3': request.session.get('prompt_3', ''),
            'prompt_4': request.session.get('prompt_4', ''),
            'prompt_5': request.session.get('prompt_5', ''),
            'drafts': drafts,
            'error': request.session.get('error', ''),
            'current_refine_step': current_refine_step,
            'grammar_checked': request.session.get('grammar_checked', False),
            'grammar_result': request.session.get('grammar_result', ''),
        })
      
    def post(self, request, *args, **kwargs):
        print("POST: Method called")
        print(f"POST data: {request.POST}")

        # Getting form data
        topic = request.POST.get('topic', '').strip()
        primary_keyword = request.POST.get('primary_keyword', '').strip()
        additional_keywords = request.POST.get('additional_keywords', '').strip()
        prompt_1 = request.POST.get('prompt_1', '').strip()
        prompt_2 = request.POST.get('prompt_2', '').strip()
        prompt_3 = request.POST.get('prompt_3', '').strip()
        prompt_4 = request.POST.get('prompt_4', '').strip()
        prompt_5 = request.POST.get('prompt_5', '').strip()
        feedback = request.POST.get('feedback', '').strip()
        action = request.POST.get('action')
        publish_date = request.POST.get('publish_date', '').strip()  # New field set up for scheduling
        drafts = request.session.get('prompt_tier_drafts', [])
        current_refine_step = request.session.get('current_refine_step', 1)
        grammar_checked = request.session.get('grammar_checked', False)
        print(f"Action: {action}, Drafts before: {drafts}, Current refine step: {current_refine_step}, Grammar checked: {grammar_checked}")
        
        # Saving form data to session
        request.session['topic'] = topic
        request.session['primary_keyword'] = primary_keyword
        request.session['additional_keywords'] = additional_keywords
        request.session['prompt_1'] = prompt_1
        request.session['prompt_2'] = prompt_2
        request.session['prompt_3'] = prompt_3
        request.session['prompt_4'] = prompt_4
        request.session['prompt_5'] = prompt_5
        request.session['error'] = ''
        print(f"Saved to session - prompts: {[prompt_1, prompt_2, prompt_3, prompt_4, prompt_5]}")

        # Handling actions
        if action == 'generate':
            print("POST: Generate button clicked")
            drafts = []
            current_refine_step = 1
            grammar_checked = False
            request.session['grammar_result'] = ''
            if not topic or not primary_keyword or not prompt_1:
                request.session['error'] = "Please provide a topic, primary keyword, and at least Prompt 1."
            else:
                prompt = (
                    f"{prompt_1} Ensure the article uses the primary keyword '{primary_keyword}' "
                    f"1-2 times. Include additional keywords '{additional_keywords}' naturally. "
                    f"Start the article with a markdown heading (e.g., # Article Title) for the title."
                )
                model = genai.GenerativeModel('gemini-1.5-flash')
                try:
                    response = model.generate_content(prompt)
                    draft_1 = response.text.strip()
                    drafts.append({'content': draft_1})
                    print(f"Generated draft 1: {draft_1}")
                except Exception as e:
                    request.session['error'] = f"Error generating content: {str(e)}"
                    print(f"Error generating draft 1: {str(e)}")
            request.session['prompt_tier_drafts'] = drafts
            request.session['current_refine_step'] = current_refine_step
            request.session['grammar_checked'] = grammar_checked

        elif action == 'refine':
            print(f"POST: Refine button clicked, current_refine_step: {current_refine_step}")
            if not drafts:
                request.session['error'] = "No draft to refine. Please generate a draft first."
            else:
                prompts = [prompt_1, prompt_2, prompt_3, prompt_4, prompt_5]
                if current_refine_step > 5:
                    request.session['error'] = "All prompts have been processed."
                else:
                    current_prompt = prompts[current_refine_step - 1]
                    if not current_prompt:
                        request.session['error'] = f"Please provide feedback in Prompt {current_refine_step}."
                    else:
                        prev_draft = drafts[-1]['content']
                        prompt = (
                            f"Refine this article: '{prev_draft}' based on feedback: '{current_prompt}'. "
                            f"Maintain the primary keyword '{primary_keyword}' usage and include additional keywords '{additional_keywords}' naturally. "
                            f"Ensure the article starts with a markdown heading (e.g., # Article Title) for the title."
                        )
                        if feedback:
                            prompt += f" Additional user feedback: '{feedback}'. Incorporate this feedback as well."
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        try:
                            response = model.generate_content(prompt)
                            new_draft = response.text.strip()
                            drafts[-1] = {'content': new_draft}
                            print(f"Refined draft with Prompt {current_refine_step}: {new_draft}")
                            current_refine_step += 1
                        except Exception as e:
                            request.session['error'] = f"Error refining content: {str(e)}"
                            print(f"Error refining with Prompt {current_refine_step}: {str(e)}")
            request.session['prompt_tier_drafts'] = drafts
            request.session['current_refine_step'] = current_refine_step
            
        elif action == 'check_grammar':
            print("POST: Check Grammar button clicked")
            if not drafts:
                request.session['error'] = "No draft to check. Please generate a draft first."
            else:
                final_draft = drafts[-1]['content']
                if "Error" in final_draft:
                    request.session['error'] = "Cannot check grammar due to previous errors."
                else:
                    url = "https://api.languagetool.org/v2/check"
                    data = {
                        'text': final_draft,
                        'language': 'en-US'
                    }
                    try:
                        response = requests.post(url, data=data)
                        result = response.json()
                        matches = result.get('matches', [])
                        if matches:
                            fixed_text = final_draft
                            offset_shift = 0
                            for match in matches:
                                start = match['offset'] + offset_shift
                                length = match['length']
                                replacement = match['replacements'][0]['value'] if match['replacements'] else fixed_text[start:start+length]
                                fixed_text = fixed_text[:start] + replacement + fixed_text[start+length:]
                                offset_shift += len(replacement) - length
                            drafts[-1] = {'content': fixed_text}
                            request.session['grammar_result'] = f"Applied {len(matches)} grammar fixes."
                            print(f"Applied {len(matches)} grammar fixes.")
                        else:
                            request.session['grammar_result'] = "No grammar issues found."
                            print("No grammar issues found.")
                        grammar_checked = True
                    except Exception as e:
                        request.session['error'] = f"Grammar check failed: {str(e)}"
                        request.session['grammar_result'] = f"Grammar check failed: {str(e)}"
                        print(f"Error in grammar zap: {str(e)}")
            request.session['prompt_tier_drafts'] = drafts 
            request.session['grammar_checked'] = grammar_checked

        elif action == 'publish':
            print("POST: Publish button clicked")
            if not drafts:
                request.session['error'] = "No content generated to publish."
            elif not publish_date:
                request.session['error'] = "Please provide a publish date and time."
            else:
                final_draft = drafts[-1]['content']
                print(f"Final content before publishing: {final_draft}")
                if "Error" in final_draft:
                    request.session['error'] = "Cannot publish due to previous errors."
                else:
                    # Applying grammar zap if not already done
                    if not grammar_checked:
                        url = "https://api.languagetool.org/v2/check"
                        data = {
                            'text': final_draft,
                            'language': 'en-US'
                        }
                        try:
                            response = requests.post(url, data=data)
                            result = response.json()
                            matches = result.get('matches', [])
                            if matches:
                                fixed_text = final_draft
                                offset_shift = 0
                                for match in matches:
                                    start = match['offset'] + offset_shift
                                    length = match['length']
                                    replacement = match['replacements'][0]['value'] if match['replacements'] else fixed_text[start:start+length]
                                    fixed_text = fixed_text[:start] + replacement + fixed_text[start+length:]
                                    offset_shift += len(replacement) - length
                                final_draft = fixed_text
                                print(f"Applied {len(matches)} grammar fixes during publish.")
                            else:
                                print("No grammar issues found during publish.")
                        except Exception as e:
                            request.session['error'] = f"Grammar check failed: {str(e)}"
                            print(f"Error in grammar zap during publish: {str(e)}")

                    # Extracting AI-generated title 
                    lines = final_draft.split('\n')
                    generated_title = topic
                    for line in lines:
                        if line.strip().startswith('#'):
                            generated_title = line.strip().replace('#', '').strip()
                            break
                        
                    # Generating SEO summary (meta description) - Made anonymous
                    seo_summary = f"{generated_title} - Explore insights on {primary_keyword} and more."

                    # Converting publish_date to ISO format for Airtable
                    try:
                        publish_date_iso = datetime.strptime(publish_date, '%Y-%m-%dT%H:%M').isoformat() + '.000Z'
                    except ValueError as e:
                        request.session['error'] = f"Invalid date format: {str(e)}"
                        print(f"Date format error: {str(e)}")
                        return render(request, self.template_name, {
                            'topic': topic,
                            'primary_keyword': primary_keyword,
                            'additional_keywords': additional_keywords,
                            'prompt_1': prompt_1,
                            'prompt_2': prompt_2,
                            'prompt_3': prompt_3,
                            'prompt_4': prompt_4,
                            'prompt_5': prompt_5,
                            'drafts': drafts,
                            'error': request.session.get('error', ''),
                            'current_refine_step': current_refine_step,
                            'grammar_checked': grammar_checked,
                            'grammar_result': request.session.get('grammar_result', ''),
                        })

                    # Getting the current timestamp for the "Created At" field (without microseconds)
                    created_at = datetime.utcnow()
                    created_at_iso = created_at.strftime('%Y-%m-%dT%H:%M:%S') + '.000Z'

                    # Sending data to Airtable
                    airtable_api_key = config('AIRTABLE_API_KEY')
                    airtable_base_id = config('AIRTABLE_BASE_ID')
                    airtable_table_name = 'Blog Posts'
                    airtable_url = f"https://api.airtable.com/v0/{airtable_base_id}/{airtable_table_name}"

                    # Debugging: Print the API details
                    print(f"Airtable API Key (first 5 chars): {airtable_api_key[:5]}...")
                    print(f"Airtable Base ID: {airtable_base_id}")
                    print(f"Airtable Table Name: {airtable_table_name}")
                    print(f"Airtable URL: {airtable_url}")
                    data = {
                        'records': [{
                            'fields': {
                                'Title': generated_title,
                                'Content': final_draft,
                                'Primary Keyword': primary_keyword,
                                'Additional Keywords': additional_keywords,
                                'SEO Summary': seo_summary,
                                'Publish Date': publish_date_iso,
                                'Status': 'Scheduled',
                                'Created At': created_at_iso  # Good to note when the blog request was generated, helps to keep track
                            }
                        }]
                    }
                    print(f"Data being sent to Airtable: {json.dumps(data, indent=2)}")

                    headers = {
                        'Authorization': f'Bearer {airtable_api_key}',
                        'Content-Type': 'application/json'
                    }

                    try:
                        response = requests.post(airtable_url, headers=headers, json=data)
                        print(f"Airtable response status code: {response.status_code}")
                        print(f"Airtable response text: {response.text}")
                        if response.status_code == 200:
                            print(f"Blog scheduled in Airtable: {generated_title}")
                            # Clearing session data after successful scheduling
                            request.session['prompt_tier_drafts'] = []
                            request.session['topic'] = ''
                            request.session['primary_keyword'] = ''
                            request.session['additional_keywords'] = ''
                            request.session['prompt_1'] = ''
                            request.session['prompt_2'] = ''
                            request.session['prompt_3'] = ''
                            request.session['prompt_4'] = ''
                            request.session['prompt_5'] = ''
                            request.session['error'] = ''
                            request.session['grammar_checked'] = False
                            request.session['grammar_result'] = ''
                            request.session['current_refine_step'] = 1
                            request.session.modified = True
                            return redirect('blog-home')
                        else:
                            request.session['error'] = f"Failed to schedule blog in Airtable: {response.text}"
                            print(f"Airtable error: {response.text}")
                    except Exception as e:
                        request.session['error'] = f"Error sending to Airtable: {str(e)}"
                        print(f"Error sending to Airtable: {str(e)}")
            request.session['prompt_tier_drafts'] = drafts
        
        request.session.modified = True
        print(f"Drafts after: {drafts}, Current refine step: {current_refine_step}, Grammar checked: {grammar_checked}")
        return render(request, self.template_name, {
            'topic': topic,
            'primary_keyword': primary_keyword,
            'additional_keywords': additional_keywords,
            'prompt_1': prompt_1,
            'prompt_2': prompt_2,
            'prompt_3': prompt_3,
            'prompt_4': prompt_4,
            'prompt_5': prompt_5,
            'drafts': drafts,
            'error': request.session.get('error', ''),
            'current_refine_step': current_refine_step,
            'grammar_checked': grammar_checked,
            'grammar_result': request.session.get('grammar_result', ''),
        })
        
        