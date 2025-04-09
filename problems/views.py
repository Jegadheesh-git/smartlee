from django.shortcuts import render, redirect, get_object_or_404
from .models import Problem, RevisionSchedule, DailyRevision
from django.utils import timezone
from datetime import timedelta, date
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.utils.timezone import localdate
from django.db.models import Count, Q
from django.http import HttpResponse
from collections import defaultdict, Counter

import requests
from bs4 import BeautifulSoup


def generate_summary(title, url):
    import requests
    import os

    TOGETHER_API_KEY = "c39d010fe37ff9008670dd47954c9b9706f9813647e6e1be6b9363ab7233b991"
    prompt = f"""Summarize the problem '{title}' from this URL: {url}.

Use bullet points to cover all approaches mentioned. dont leave anything. Use HTML with <ul> and <li> if necessary."""

    headers = {
        "Authorization": f"Bearer {TOGETHER_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "mistralai/Mixtral-8x7B-Instruct-v0.1",
        "messages": [
            {"role": "system", "content": "You're a helpful assistant that summarizes coding problems."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 300
    }

    try:
        response = requests.post("https://api.together.xyz/v1/chat/completions", headers=headers, json=data)
        print("Status:", response.status_code)
        print("Raw response:", response.text)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        print("Error from Together API:", e)
        return "Summary could not be generated."

def generate_summary_with_ollama(problem_title, problem_url):
    try:
        # Step 1: Fetch content from the URL
        response = requests.get(problem_url, timeout=10)
        response.raise_for_status()

        # Step 2: Parse HTML and extract text
        soup = BeautifulSoup(response.text, 'html.parser')

        # Remove script and style tags
        for tag in soup(['script', 'style']):
            tag.decompose()

        # Get visible text content
        page_text = soup.get_text(separator=' ', strip=True)

        # Limit to first 1000 characters to keep prompt small
        content_snippet = page_text[:1000]

        # Step 3: Send prompt to local LLM
        prompt ="""
        You are given the content of a coding problem page. Generate a **single, concise summary** that:

- Starts with a 1–2 line **problem statement**.
- Includes only the **approaches discussed in the given page**—do not add any external or assumed approaches.
- For each approach:
  - Use bullet points (`<ul><li>`) to list them clearly.
  - Briefly describe the logic.
  - Include **time and space complexity**.
- Ends with **key takeaways** in a separate `<ul>` block.
- Format everything using **semantic HTML**, including `<h3>`, `<ul>`, and `<li>` for web integration.

Wrap the entire output inside triple backticks with `html` for rendering.

Output format:
<!-- Your concise summary in HTML format -->

        """


        ai_response = requests.post(
            'http://localhost:11434/api/generate',
            json={
                'model': 'mistral',
                'prompt': prompt,
                'stream': False
            }
        )

        summary = ai_response.json().get('response', '').strip()
        return summary or "Summary not available."
    
    except Exception as e:
        print("Error generating summary:", e)
        return "Summary not available."

    

def custom_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('problem_list')  # or your desired route
        else:
            messages.error(request, "Invalid username or password.")
    
    return render(request, 'login.html') 

def custom_logout(request):
    logout(request)
    return redirect('login')  

def signup(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        if password1 != password2:
            messages.error(request, "Passwords do not match.")
        elif User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken.")
        else:
            user = User.objects.create_user(username=username, password=password1)
            login(request, user)
            return redirect('problem_list')  # or home page

    return render(request, 'signup.html')


@login_required
def problem_list(request):
    user = request.user

    # Active and Completed Problems
    problems = Problem.objects.filter(hasCompleted=False, user=user).order_by('id')
    completed_problems = Problem.objects.filter(hasCompleted=True, user=user).order_by('-id')

    # Total counts
    total_active = problems.count()
    total_completed = completed_problems.count()
    total_topics = total_active + total_completed

    # Completed Today
    completed_today = Problem.objects.filter(
        user=user,
        hasCompleted=True,
        completed_at__date=localdate()
    ).count()

    # Pending Recalls
    pending_recalls = RevisionSchedule.objects.filter(
        user=user,
        revision_date=localdate(),
        is_completed=False
    ).count()

    # === Difficulty count ===
    difficulty_counts = Counter()
    tag_counts = Counter()

    for problem in completed_problems:
        # Count by difficulty
        if problem.difficulty:
            difficulty_counts[problem.difficulty.strip().lower()] += 1

        # Count by tags
        if problem.tags:
            tags = [tag.strip().lower() for tag in problem.tags.split(',') if tag.strip()]
            tag_counts.update(tags)

    # Ensure keys for 'easy', 'medium', 'hard' are always present
    for key in ['easy', 'medium', 'hard']:
        if key not in difficulty_counts:
            difficulty_counts[key] = 0

    context = {
        'problems': problems,
        'completed_problems': completed_problems,
        'task_stats': {
            'total_active': total_active,
            'total_completed': total_completed,
            'total_topics': total_topics,
            'completed_today': completed_today,
            'pending_recalls': pending_recalls,
        },
        'difficulty_counts': dict(difficulty_counts),  # Always includes 'easy', 'medium', 'hard'
        'tag_counts': dict(tag_counts),
    }

    return render(request, 'problem_list.html', context)

def skip_revision(request):
    request.session['skip_revision'] = True
    return redirect('problem_list')

@require_POST
def toggle_complete(request, pk):
    problem = get_object_or_404(Problem, pk=pk)

    if request.method == 'POST':
        has_completed = problem.hasCompleted

        # Toggle status
        problem.hasCompleted = not has_completed

        if problem.hasCompleted:
            problem.completed_at = timezone.now()

            summary = generate_summary(problem.title, problem.url)

            # Create spaced repetition schedule
            intervals = [1, 2, 3, 4, 7, 9, 12, 15, 5, 5, 5, 5, 5, 5]
            for i in intervals:
                RevisionSchedule.objects.create(
                    problem=problem,
                    revision_date=date.today() + timedelta(days=i),
                    user=request.user,
                    long_notes=summary
                )
        else:
            # Reset completion time
            problem.completed_at = None

            # Delete all future and past revision entries
            RevisionSchedule.objects.filter(problem=problem).delete()

        problem.save()

    return redirect('problem_list')

def toggle_completion(request, problem_id):
    problem = get_object_or_404(Problem, id=problem_id)
    problem.hasCompleted = not problem.hasCompleted
    problem.save()
    return redirect('problem_list')

def add_problem(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        url = request.POST.get('url')
        notes = request.POST.get('notes', '')
        tags = request.POST.get('tags', '')  # get tags string
        difficulty = request.POST.get('difficulty', 'Medium')  # default to Medium

        problem = Problem.objects.create(
            title=title,
            url=url,
            notes=notes,
            tags=tags,
            difficulty=difficulty,
            user=request.user
        )
        return redirect('problem_list')
    return render(request, 'add_problem.html')

from django.utils import timezone
from datetime import date, timedelta
from django.shortcuts import render, get_object_or_404, redirect
from .models import Problem, RevisionSchedule

def edit_problem(request, pk):
    problem = get_object_or_404(Problem, pk=pk)

    if request.method == 'POST':
        problem.title = request.POST.get('title')
        problem.url = request.POST.get('url')
        problem.notes = request.POST.get('notes', '')

        has_completed = request.POST.get('hasCompleted') == 'on'

        # If marked completed now and wasn't before
        if has_completed and not problem.hasCompleted:
            problem.hasCompleted = True
            problem.completed_at = timezone.now()

            # Schedule future revisions
            intervals = [1, 2, 4, 7, 15]
            for i in intervals:
                RevisionSchedule.objects.create(
                    problem=problem,
                    revision_date=date.today() + timedelta(days=i)
                )
        else:
            problem.hasCompleted = False
            problem.completed_at = None  # optional: clear the date if unchecked

        problem.save()
        return redirect('problem_list')

    return render(request, 'edit_problem.html', {'problem': problem})


def revision_queue(request):
    today = date.today()
    # Get all due and incomplete revisions
    due_revisions = RevisionSchedule.objects.filter(
        revision_date__lte=today,
        is_completed=False,
        user=request.user
    ).order_by('-revision_date')  # Order by latest first

    seen_problems = set()
    latest_revision_entries = []

    for revision in due_revisions:
        if revision.problem_id not in seen_problems:
            latest_revision_entries.append(revision)  # Add the revision itself
            seen_problems.add(revision.problem_id)

    due_revisions = DailyRevision.objects.filter(user=request.user, last_revised_date__lt=timezone.now().date())

    return render(request, 'revision_queue.html', {'revisions': latest_revision_entries, 'due_revisions': due_revisions})


def mark_revision_complete(request, pk):
    today = date.today()
    revisions = RevisionSchedule.objects.filter(problem_id=pk, revision_date__lte=today, is_completed=False)
    print("Revisions found:", revisions.count())
    for rev in revisions:
        rev.is_completed = True
        rev.save()
    return redirect('revision_queue')

@login_required
def daily_revision_list(request):
    due_revisions = DailyRevision.objects.filter(user=request.user, last_revised_date__lt=timezone.now().date())
    return render(request, 'revision_list.html', {'revisions': due_revisions})

@login_required
def create_daily_revision(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        url = request.POST.get('url')
        description = request.POST.get('description')
        image_url = request.POST.get('image_url')

        DailyRevision.objects.create(
            user=request.user,
            title=title,
            url=url,
            description=description,
            image_url=image_url
        )
        return redirect('revision_queue')

    return render(request, 'create_revision.html')

@login_required
def mark_as_revised(request, id):
    print("method:", request.method)
    print("updayed")
    revision = DailyRevision.objects.get(id=id, user=request.user)
    revision.last_revised_date = timezone.now().date()
    revision.save()
    return redirect('revision_queue')

@login_required
def delete_problem(request, pk):
    problem = get_object_or_404(Problem, pk=pk, user=request.user)
    if request.method == 'POST':
        problem.delete()
        return redirect('problem_list')  # update redirect as needed
    return render(request, 'confirm_delete.html', {'object': problem, 'type': 'Problem'})

@login_required
def delete_dailyrevision(request, pk):
    revision = get_object_or_404(DailyRevision, pk=pk, user=request.user)
    if request.method == 'POST':
        revision.delete()
        return redirect('revision_queue')
    return render(request, 'confirm_delete.html', {'object': revision, 'type': 'Daily Revision'})

@login_required
def edit_dailyrevision(request, pk):
    revision = get_object_or_404(DailyRevision, pk=pk, user=request.user)

    if request.method == 'POST':
        revision.title = request.POST.get('title', revision.title)
        revision.url = request.POST.get('url', revision.url)
        revision.description = request.POST.get('description', revision.description)
        revision.image_url = request.POST.get('image_url', revision.image_url)
        revision.last_revised_date = request.POST.get('last_revised_date', revision.last_revised_date)
        revision.save()
        return redirect('revision_queue')

    return render(request, 'edit_dailyrevision.html', {'revision': revision})