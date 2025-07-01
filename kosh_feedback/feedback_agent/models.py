from django.db import models
from django.utils import timezone

import datetime

# Edit this to a report model, then migrate it!
class Report(models.Model):
    title=models.CharField(max_length=500)
    content=models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    # string representation of the class
    def __str__(self):
        return self.title 