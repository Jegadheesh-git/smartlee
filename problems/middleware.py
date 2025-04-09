from django.shortcuts import redirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin
from django.contrib.sessions.models import Session
from .models import RevisionSchedule
from datetime import date
import logging

logger = logging.getLogger(__name__)

class EnforceRevisionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Gracefully handle corrupted session data
        try:
            _ = request.session.items()
        except Exception as e:
            logger.warning(f"⚠️ Corrupted session detected: {e}")
            session_key = request.COOKIES.get('sessionid')
            if session_key:
                try:
                    Session.objects.filter(session_key=session_key).delete()
                except Exception as delete_error:
                    logger.warning(f"⚠️ Could not delete session: {delete_error}")
            request.session.flush()

        revision_path = reverse('revision_queue')
        ignore_path = reverse('skip_revision')
        login_path = reverse('login')
        logout_path = reverse('logout')
        signup_path = reverse('signup')

        # URL like /mark_revision_complete/23
        mark_revision_path_prefix = reverse('mark_revision_complete', kwargs={'pk': 0}).rsplit('/', 2)[0]
        mark_as_revised_path_prefix = reverse('mark_as_revised', kwargs={'id': 0}).rsplit('/', 2)[0]


        current_path = request.path

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
            current_path.startswith(mark_as_revised_path_prefix) or
            request.session.get('skip_revision', False)
        ):
            return self.get_response(request)

        if request.user.is_authenticated:
            has_pending = RevisionSchedule.objects.filter(
                revision_date__lte=date.today(),
                is_completed=False,
                user=request.user
            ).exists()

            if has_pending:
                return redirect('revision_queue')

        return self.get_response(request)
