from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Problem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    url = models.URLField()
    notes = models.TextField(blank=True)
    hasCompleted = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    tags = models.CharField(max_length=255, blank=True)
    difficulty = models.CharField(max_length=50, choices=[('Easy', 'Easy'), ('Medium', 'Medium'), ('Hard', 'Hard')], default='Medium')


    def __str__(self):
        return self.title
    
    @property
    def tag_list(self):
        if not self.tags:
            return []
        return [tag.strip() for tag in self.tags.split(',') if tag.strip()]

class RevisionSchedule(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE)
    short_notes = models.CharField(max_length=10000, null=True, blank=True)
    long_notes = models.CharField(max_length=10000, null=True, blank=True)
    revision_date = models.DateField()
    is_completed = models.BooleanField(default=False)

    def __str__(self):
        return self.problem.title + " created by " + str(self.user)

class DailyRevision(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    url = models.URLField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    image_url = models.URLField(null=True, blank=True)
    last_revised_date = models.DateField(default=timezone.now,null=True, blank=True)
    created_on = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.title}"