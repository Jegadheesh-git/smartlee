from django.db import models
from django.contrib.auth.models import User

class Problem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    url = models.URLField()
    notes = models.TextField(blank=True)
    hasCompleted = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title

class RevisionSchedule(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE)
    short_notes = models.CharField(max_length=10000, null=True, blank=True)
    long_notes = models.CharField(max_length=10000, null=True, blank=True)
    revision_date = models.DateField()
    is_completed = models.BooleanField(default=False)

    def __str__(self):
        return self.problem.title + " created by " + str(self.user)
