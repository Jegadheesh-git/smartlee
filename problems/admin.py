from django.contrib import admin
from .models import Problem, RevisionSchedule, DailyRevision

admin.site.register(Problem)
admin.site.register(RevisionSchedule)
admin.site.register(DailyRevision)
