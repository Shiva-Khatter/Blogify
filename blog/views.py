from django.shortcuts import render, get_object_or_404, redirect
import requests 
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from .models import Post, ScheduledPost
from django import forms 
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View
import google.generativeai as genai
from decouple import config
from pyairtable import Table
from datetime import datetime

# Loading the Airtable configuration
AIRTABLE_API_KEY = config('AIRTABLE_API_KEY')
AIRTABLE_BASE_ID = config('AIRTABLE_BASE_ID')
AIRTABLE_TABLE_NAME = "Blog Posts"

# Connecting to Airtable 
airtable = Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME)

def home(request):
    context = {
        'posts': Post.objects.all()
    }
    return render(request, 'blog/home.html', context)

class PostListView(ListView):
    model = Post
    template_name = 'blog/home.html'
    context_object_name = 'posts'
    ordering = ['-date_posted']
    paginate_by = 5
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['latest_posts'] = Post.objects.all().order_by('-date_posted')[:5]
        return context

class UserPostListView(ListView):
    model = Post
    template_name = 'blog/user_posts.html'
    context_object_name = 'posts'
    paginate_by = 5
    
    def get_queryset(self):
        user = get_object_or_404(User, username=self.kwargs.get('username'))
        return Post.objects.filter(author=user).order_by('-date_posted')
    
class PostDetailView(DetailView):
    model = Post
    
class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    fields = ['title', 'content']
       
    def form_valid(self, form):
        form.instance.author = self.request.user 
        return super().form_valid(form)

class PostUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Post
    fields = ['title', 'content']
       
    def form_valid(self, form):
        form.instance.author = self.request.user 
        return super().form_valid(form)
    
    def test_func(self):
        post = self.get_object()
        if self.request.user==post.author:
            return True
        return False  
    
class PostDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Post
    success_url = '/'
    
    def test_func(self):
        post = self.get_object()
        if self.request.user==post.author:
            return True
        return False  

def about(request):
    return render(request, 'blog/about.html', {'title': 'About'})

genai.configure(api_key=config('GEMINI_API_KEY'))
class GenerateBlogView(LoginRequiredMixin, View):
    template_name = 'blog/generate.html'

    def get(self, request):
        drafts = request.session.get('drafts', [])
        topic = request.GET.get('topic', request.session.get('topic', ''))
        primary_keyword = request.GET.get('primary_keyword', request.session.get('primary_keyword', ''))
        additional_keywords = request.GET.get('additional_keywords', request.session.get('additional_keywords', ''))
        return render(request, self.template_name, {
            'topic': topic,
            'primary_keyword': primary_keyword,
            'additional_keywords': additional_keywords,
            'prompt_1': request.session.get('prompt_1', ''),
            'prompt_2': request.session.get('prompt_2', ''),
            'prompt_3': request.session.get('prompt_3', ''),
            'prompt_4': request.session.get('prompt_4', ''),
            'drafts': drafts,
        })
    def post(self, request):
        topic = request.POST.get('topic')
        primary_keyword = request.POST.get('primary_keyword')
        additional_keywords = request.POST.get('additional_keywords')
        prompt_1 = request.POST.get('prompt_1')
        prompt_2 = request.POST.get('prompt_2')
        prompt_3 = request.POST.get('prompt_3')
        prompt_4 = request.POST.get('prompt_4')
        action = request.POST.get('action')
        drafts = request.session.get('drafts', [])
        print(f"Action: {action}, Drafts before: {drafts}")

        if action == 'generate':
            drafts = []
            prompt = (
                f"{prompt_1} Ensure the article is 500 words and uses the primary keyword '{primary_keyword}' "
                f"5-10 times (1-2% density) for SEO. Include additional keywords '{additional_keywords}' naturally."
            )
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            draft_1 = response.text
            drafts.append({'prompt': prompt_1, 'content': draft_1})
            request.session['drafts'] = drafts
            request.session['topic'] = topic
            request.session['primary_keyword'] = primary_keyword
            request.session['additional_keywords'] = additional_keywords 
            request.session['prompt_1'] = prompt_1
            request.session.modified = True

        elif action == 'refine_2':
            if not drafts:
                return render(request, self.template_name, {
                    'topic': topic,
                    'primary_keyword': primary_keyword,
                    'additional_keywords': additional_keywords,
                    'prompt_1': prompt_1,
                    'drafts': drafts,
                    'error': 'No draft to refine. Please generate a draft first.'
                })
                
            if not prompt_2:
                return render(request, self.template_name, {
                    'topic': topic,
                    'primary_keyword': primary_keyword,
                    'additional_keywords': additional_keywords,
                    'prompt_1': prompt_1,
                    'drafts': drafts,
                    'error': 'Please provide feedback in Prompt 2.'
                })
            prev_draft = drafts[-1]['content']
            prompt = f"Refine this 500-word article: '{prev_draft}' based on feedback: '{prompt_2}'. Maintain keyword density and length."
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            draft_2 = response.text
            drafts.append({'prompt': prompt_2, 'content': draft_2})
            request.session['drafts'] = drafts
            request.session['prompt_2'] = prompt_2
            request.session.modified = True

        elif action == 'refine_3':
            if not drafts or len(drafts) < 2:
                return render(request, self.template_name, {
                    'topic': topic,
                    'primary_keyword': primary_keyword,
                    'additional_keywords': additional_keywords,
                    'prompt_1': prompt_1,
                    'prompt_2': prompt_2,
                    'drafts': drafts,
                    'error': 'Complete Prompt 2 first.'
                })

        
            if not prompt_3:
                return render(request, self.template_name, {
                    'topic': topic,
                    'primary_keyword': primary_keyword,
                    'additional_keywords': additional_keywords,
                    'prompt_1': prompt_1,
                    'prompt_2': prompt_2,
                    'drafts': drafts,
                    'error': 'Please provide feedback in Prompt 3.'
                })
            prev_draft = drafts[-1]['content']
            prompt = f"Refine this 500-word article: '{prev_draft}' based on feedback: '{prompt_3}'. Maintain keyword density and length."
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            draft_3 = response.text
            drafts.append({'prompt': prompt_3, 'content': draft_3})
            request.session['drafts'] = drafts
            request.session['prompt_3'] = prompt_3
            request.session.modified = True

        elif action == 'refine_4':
            if not drafts or len(drafts) < 3:
                return render(request, self.template_name, {
                    'topic': topic,
                    'primary_keyword': primary_keyword,
                    'additional_keywords': additional_keywords,
                    'prompt_1': prompt_1,
                    'prompt_2': prompt_2,
                    'prompt_3': prompt_3,
                    'drafts': drafts,
                    'error': 'Complete Prompt 3 first.'
                })
            if not prompt_4:
                return render(request, self.template_name, {
                    'topic': topic,
                    'primary_keyword': primary_keyword,
                    'additional_keywords': additional_keywords,
                    'prompt_1': prompt_1,
                    'prompt_2': prompt_2,
                    'prompt_3': prompt_3,
                    'drafts': drafts,
                    'error': 'Please provide feedback in Prompt 4.'
                }) 
            prev_draft = drafts[-1]['content']
            prompt = f"Refine this 500-word article: '{prev_draft}' based on feedback: '{prompt_4}'. Maintain the same keyword density and word length untill explicitly mentioned by the user."
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            draft_4 = response.text
            drafts.append({'prompt': prompt_4, 'content': draft_4})
            request.session['drafts'] = drafts
            request.session['prompt_4'] = prompt_4
            request.session.modified = True
              
        elif action == 'check_grammar':
            if not drafts or len(drafts) < 4:
                return render(request, self.template_name, {
                    'topic': topic,
                    'primary_keyword': primary_keyword,
                    'additional_keywords': additional_keywords,
                    'prompt_1': prompt_1,
                    'prompt_2': prompt_2,
                    'prompt_3': prompt_3,
                    'prompt_4': prompt_4,
                    'drafts': drafts,
                    'error': 'Complete all prompts up to Prompt 4 before checking grammar.'
                })

            if len(drafts) > 4:  # If the blog is already grammar zapped  
                return render(request, self.template_name, {
                    'topic': topic,
                    'primary_keyword': primary_keyword,
                    'additional_keywords': additional_keywords,
                    'prompt_1': prompt_1,
                    'prompt_2': prompt_2,
                    'prompt_3': prompt_3,
                    'prompt_4': prompt_4,
                    'drafts': drafts,
                    'grammar_checked': request.session.get('grammar_checked', False),
                    'grammar_result': request.session.get('grammar_result', ''),
                    'error': 'Grammar already checked for this draft.'
                })
            final_draft = drafts[-1]['content']
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
                    drafts.append({'prompt': 'AI Grammar Zap', 'content': fixed_text})
                    grammar_result = f"Applied {len(matches)} grammar fixes."
                else:
                    drafts.append({'prompt': 'AI Grammar Zap', 'content': final_draft})
                    grammar_result = "No grammar issues found."
            except Exception as e:
                grammar_result = f"Grammar check failed: {str(e)}"
                drafts.append({'prompt': 'AI Grammar Zap', 'content': final_draft})
            request.session['drafts'] = drafts 
            request.session['grammar_checked'] = True
            request.session['grammar_result'] = grammar_result
            request.session.modified = True

        elif action == 'publish':
            if not drafts or len(drafts) < 4:
                return render(request, self.template_name, {
                    'topic': topic,
                    'primary_keyword': primary_keyword,
                    'additional_keywords': additional_keywords,
                    'prompt_1': prompt_1,
                    'prompt_2': prompt_2,
                    'prompt_3': prompt_3,
                    'prompt_4': prompt_4,
                    'drafts': drafts,
                    'error': 'Complete all prompts up to Prompt 4 before publishing.'
                })
                
            final_draft = drafts[-1]['content']
            lines = final_draft.split('\n')
            generated_title = topic
            for line in lines:
                if line.strip().startswith('#'):
                    generated_title = line.strip().replace('#', '').strip()
                    break
            post = Post(
                title=generated_title,
                content=final_draft,
                author=request.user,
                seo_keywords=f"{primary_keyword}, {additional_keywords}",
                is_draft=False
            )
            post.save()
            # Deleting the matching ScheduledPost if they already exists
            ScheduledPost.objects.filter(
                topic=topic,
                primary_keyword=primary_keyword,
                additional_keywords=additional_keywords
            ).delete()
            request.session['drafts'] = []
            request.session['topic'] = ''
            request.session['primary_keyword'] = ''
            request.session['additional_keywords'] = ''
            request.session['prompt_1'] = ''
            request.session['prompt_2'] = ''
            request.session['prompt_3'] = ''
            request.session['prompt_4'] = ''
            request.session['grammar_checked'] = False
            request.session['grammar_result'] = ''
            request.session.modified = True
            return redirect('blog-home')

        elif action == 'publish_to_airtable':
            if not drafts or len(drafts) < 4:
                return render(request, self.template_name, {
                    'topic': topic,
                    'primary_keyword': primary_keyword,
                    'additional_keywords': additional_keywords,
                    'prompt_1': prompt_1,
                    'prompt_2': prompt_2,
                    'prompt_3': prompt_3,
                    'prompt_4': prompt_4,
                    'drafts': drafts,
                    'error': 'Complete all prompts up to Prompt 4 before publishing.'
                })

            final_draft = drafts[-1]['content']
            lines = final_draft.split('\n')
            generated_title = topic
            for line in lines:
                if line.strip().startswith('#'):
                    generated_title = line.strip().replace('#', '').strip()
                    break

            # Setting publish date to now for immediate publishing
            publish_date = datetime.now()
            status = "Published"

            # Preparing the record for Airtable
            record = {
                "Title": generated_title,
                "Content": final_draft,
                "Primary Keyword": primary_keyword,
                "Additional Keywords": additional_keywords,
                "Publish Date": publish_date.isoformat(),
                "Status": status,
            }

            try:
                # Saving the record to Airtable
                airtable.create(record)
                # Clearing session data
                request.session['drafts'] = []
                request.session['topic'] = ''
                request.session['primary_keyword'] = ''
                request.session['additional_keywords'] = ''
                request.session['prompt_1'] = ''
                request.session['prompt_2'] = ''
                request.session['prompt_3'] = ''
                request.session['prompt_4'] = ''
                request.session['grammar_checked'] = False
                request.session['grammar_result'] = ''
                request.session.modified = True
                return redirect('blog-home')
            except Exception as e:
                return render(request, self.template_name, {
                    'topic': topic,
                    'primary_keyword': primary_keyword,
                    'additional_keywords': additional_keywords,
                    'prompt_1': prompt_1,
                    'prompt_2': prompt_2,
                    'prompt_3': prompt_3,
                    'prompt_4': prompt_4,
                    'drafts': drafts,
                    'error': f"Error saving to Airtable: {str(e)}"
                })

        elif action == 'schedule_to_airtable':
            if not drafts or len(drafts) < 4:
                return render(request, self.template_name, {
                    'topic': topic,
                    'primary_keyword': primary_keyword,
                    'additional_keywords': additional_keywords,
                    'prompt_1': prompt_1,
                    'prompt_2': prompt_2,
                    'prompt_3': prompt_3,
                    'prompt_4': prompt_4,
                    'drafts': drafts,
                    'error': 'Complete all prompts up to Prompt 4 before scheduling.'
                })

            final_draft = drafts[-1]['content']
            lines = final_draft.split('\n')
            generated_title = topic
            for line in lines:
                if line.strip().startswith('#'):
                    generated_title = line.strip().replace('#', '').strip()
                    break

            publish_date_str = request.POST.get('publish_date')
            if not publish_date_str:
                return render(request, self.template_name, {
                    'topic': topic,
                    'primary_keyword': primary_keyword,
                    'additional_keywords': additional_keywords,
                    'prompt_1': prompt_1,
                    'prompt_2': prompt_2,
                    'prompt_3': prompt_3,
                    'prompt_4': prompt_4,
                    'drafts': drafts,
                    'error': 'Please provide a publish date for scheduling.'
                })

            try:
                publish_date = datetime.strptime(publish_date_str, "%Y-%m-%dT%H:%M")
                current_time = datetime.now()
                status = "Scheduled" if publish_date > current_time else "Published"
            except ValueError:
                return render(request, self.template_name, {
                    'topic': topic,
                    'primary_keyword': primary_keyword,
                    'additional_keywords': additional_keywords,
                    'prompt_1': prompt_1,
                    'prompt_2': prompt_2,
                    'prompt_3': prompt_3,
                    'prompt_4': prompt_4,
                    'drafts': drafts,
                    'error': 'Invalid date format. Use YYYY-MM-DDTHH:MM.'
                })

            # Preparing the record for Airtable
            record = {
                "Title": generated_title,
                "Content": final_draft,
                "Primary Keyword": primary_keyword,
                "Additional Keywords": additional_keywords,
                "Publish Date": publish_date.isoformat(),
                "Status": status,
            }

            try:
                # Saving the record to Airtable
                airtable.create(record)
                # Clearing session data
                request.session['drafts'] = []
                request.session['topic'] = ''
                request.session['primary_keyword'] = ''
                request.session['additional_keywords'] = ''
                request.session['prompt_1'] = ''
                request.session['prompt_2'] = ''
                request.session['prompt_3'] = ''
                request.session['prompt_4'] = ''
                request.session['grammar_checked'] = False
                request.session['grammar_result'] = ''
                request.session.modified = True
                return redirect('blog-home')
            except Exception as e:
                return render(request, self.template_name, {
                    'topic': topic,
                    'primary_keyword': primary_keyword,
                    'additional_keywords': additional_keywords,
                    'prompt_1': prompt_1,
                    'prompt_2': prompt_2,
                    'prompt_3': prompt_3,
                    'prompt_4': prompt_4,
                    'drafts': drafts,
                    'error': f"Error saving to Airtable: {str(e)}"
                })

        print(f"Drafts after: {drafts}")
        return render(request, self.template_name, {
            'topic': topic,
            'primary_keyword': primary_keyword,
            'additional_keywords': additional_keywords,
            'prompt_1': prompt_1,
            'prompt_2': prompt_2,
            'prompt_3': prompt_3,
            'prompt_4': prompt_4,
            'drafts': drafts,
            'grammar_checked': request.session.get('grammar_checked', False),
            'grammar_result': request.session.get('grammar_result', ''),
        })

def sidebar_context(request):
    return {
        'latest_posts': Post.objects.all().order_by('-date_posted')[:5]
    }

from django.contrib.admin.views.decorators import staff_member_required

class ScheduledPostForm(forms.ModelForm):
    class Meta:
        model = ScheduledPost
        fields = ['topic', 'primary_keyword', 'additional_keywords', 'scheduled_datetime']
        widgets = {
            'scheduled_datetime': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

@staff_member_required(login_url='login')
def auto_schedule(request):
    if not request.user.is_superuser:
        return redirect('blog-home')
    
    if request.method == 'POST':
        form = ScheduledPostForm(request.POST)
        if form.is_valid():
            scheduled_post = form.save(commit=False)
            scheduled_post.created_by = request.user
            scheduled_post.save()
            return redirect('auto-schedule')
    else:
        form = ScheduledPostForm()
    
    scheduled_posts = ScheduledPost.objects.all().order_by('-scheduled_datetime')
    return render(request, 'blog/auto_schedule.html', {
        'form': form,
        'scheduled_posts': scheduled_posts,
    })

@staff_member_required(login_url='login')
def delete_scheduled_post(request, pk):
    if not request.user.is_superuser:
        return redirect('blog-home')
    ScheduledPost.objects.filter(id=pk, created_by=request.user).delete()
    return redirect('auto-schedule')