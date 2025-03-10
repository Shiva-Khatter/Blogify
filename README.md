# Blogify

**AI-powered blog generator built with Django and Gemini API.**  
Create, refine, and zap grammar in four drafts—blogging, simplified!  

---

## Overview

Blogify is a Django-based web application that blends AI creativity with a polished blogging platform. Designed as an internship project, it lets users generate 500-word blog posts through a four-prompt refinement process powered by Google’s Gemini API, with an optional "AI Grammar Zap" using LanguageTool API. But it’s more than just AI—Blogify is a full-fledged website with user auth, a sleek navbar, and a cozy brown `#8b5e3b` theme, all built from scratch with Django’s magic.

---

## Features

### Django Website Core
- **User Authentication**: Login, logout, register, and profile pages—secured with Django’s built-in auth system. Only logged-in users can generate or publish posts.  
- **Navbar**: Responsive Bootstrap 4 navbar with "Generate with AI" (complete with a ✨ sparkle on hover), "New Post," "Home," "About," and user options.  
- **Templates**: Clean, reusable HTML templates (`base.html`, `generate.html`) styled with Bootstrap and custom `main.css` for a warm brown aesthetic (`#8b5e3b` cards, `#e8dcc7` background).  
- **Post Management**: View, create, and publish posts with SEO-friendly keyword integration, stored in a Django SQLite database (`Post` model).  
- **Sidebar**: Dynamic "Latest Posts" widget pulls recent posts with clickable titles—pure Django template logic.  
- **Session Persistence**: Drafts and inputs stay alive across requests using Django’s session framework—no data loss mid-process!
- **Auto-Schedule**: The superuser has the access to the 'Auto-Schedule' Feature that helps them to schedule what blogs will be posted at what date and time, the predefined keywords and topics help to generate blogs automatically as scheduled.

### AI-Powered Blog Generation
- **Four-Prompt Flow**:  
  1. **Prompt 1**: Initial 500-word draft with 1–2% keyword density (via Gemini API).  
  2. **Prompt 2–4**: Refine drafts with user feedback—stacked in a chatbot-style UI (`generate.html`).  
- **AI Grammar Zap**: Optional post-Draft 4 grammar check with LanguageTool API—fixes errors and adds a fifth draft card.  
- **Publishing**: Final draft (Draft 4 or 5) becomes a `Post` object, with the title pulled from Markdown headings.

### UI Highlights
- **Hover Tooltips**: "Generate with AI" (Gemini API) and "AI Grammar Zap" (LanguageTool API) buttons show tech details on hover—Bootstrap-powered with `#8b5e3b` styling.  
- **Draft Cards**: Stacked cards display each draft’s prompt and content, with word count and brown `#8b5e3b` borders.  
- **Buttons**: Custom `.btn-custom-brown` class with hover scaling—smooth and interactive.

---

## Tech Stack

- **Backend**: Django 5.1.1 (Python 3.12)  
  - Views: `GenerateBlogView` (class-based) handles all generation logic.  
  - Models: `Post` for blog storage, with fields for title, content, author, and SEO keywords.  
  - Sessions: Store drafts and inputs between requests.  
- **Frontend**: Bootstrap 4, custom `main.css`  
  - Templates: `base.html` (navbar, sidebar), `generate.html` (generation UI).  
  - Styling: `#8b5e3b` brown theme, `#e8dcc7` background, subtle shadows.  
- **AI APIs**:  
  - Google Gemini API (`gemini-1.5-flash`) for draft generation.  
  - LanguageTool API (free tier) for grammar fixes.  
- **Database**: SQLite (Django default)—lightweight and local.

---

## How It Works

1. **Start**: Log in, hit "Generate with AI" in the navbar (✨ sparkles on hover!).  
2. **Input**: Enter a topic, primary keyword, additional keywords, and Prompt 1 in `generate.html`.  
3. **Generate**: Gemini API crafts a 500-word Draft 1, stored in session and displayed in a card.  
4. **Refine**: Add Prompts 2–4 to tweak the draft—each builds a new card, stacking chatbot-style.  
5. **Zap**: After Draft 4, click "AI Grammar Zap" (hover for LanguageTool info) for a fifth draft with fixes.  
6. **Publish**: Hit "Publish Final Draft" to save the latest draft as a `Post`, resetting the session.  
7. **Explore**: Navbar and sidebar link to Home, About, and latest posts—full Django website vibes!

