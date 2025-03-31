from django.urls import path
from .views import PostListView, PostDetailView, PostCreateView, PostUpdateView, PostDeleteView, UserPostListView
from . import views
from .blogcraft_views import BlogCraftView
from .seo_views import SEOBlogGeneratorView  # Importing from seo_views.py

urlpatterns = [
    path('', PostListView.as_view(), name='blog-home'),
    path('user/<str:username>', UserPostListView.as_view(), name='user-posts'),
    path('post/<int:pk>/', PostDetailView.as_view(), name='post-detail'),
    path('post/new/', PostCreateView.as_view(), name='post-create'),
    path('post/<int:pk>/update/', PostUpdateView.as_view(), name='post-update'),
    path('post/<int:pk>/delete/', PostDeleteView.as_view(), name='post-delete'),
    path('about/', views.about, name='blog-about'),
    path('generate/', views.GenerateBlogView.as_view(), name='blog-generate'),
    path('auto-schedule/', views.auto_schedule, name='auto-schedule'),
    path('auto-schedule/delete/<int:pk>/', views.delete_scheduled_post, name='delete-scheduled-post'),
    path('blogcraft/', BlogCraftView.as_view(), name='blogcraft'),
    path('seo-generator/', SEOBlogGeneratorView.as_view(), name='seo-generator'),  # Updated reference
]