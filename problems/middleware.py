from django.shortcuts import redirect
from django.urls import reverse
from .models import RevisionSchedule
from datetime import date

class EnforceRevisionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        revision_path = reverse('revision_queue')
        ignore_path = reverse('skip_revision')
        login_path = reverse('login')
        logout_path = reverse('logout')
        signup_path = reverse('signup')
        mark_revision_path_prefix = reverse('mark_revision_complete', kwargs={'pk': 0}).rsplit('/', 2)[0]
        current_path = request.path

        # Allow paths that should not be intercepted
        exempt_paths = [
            revision_path,
            ignore_path,
            login_path,
            logout_path,
            signup_path,
        ]

        if (
            current_path in exempt_paths or
            current_path.startswith('/admin') or
            current_path.startswith('/static') or
            current_path.startswith(mark_revision_path_prefix) or
            request.session.get('skip_revision', False)
        ):
            return self.get_response(request)

        # Check for pending revisions
        pending = RevisionSchedule.objects.filter(
            revision_date__lte=date.today(),
            is_completed=False,
            problem__user=request.user if request.user.is_authenticated else None
        ).exists()

        if request.user.is_authenticated and pending:
            return redirect('revision_queue')

        return self.get_response(request)
