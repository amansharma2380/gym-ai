from django.db import models
from django.contrib.auth.models import User

class MemberProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='memberprofile')
    phone = models.CharField(max_length=20, blank=True)
    age = models.PositiveSmallIntegerField(null=True, blank=True)
    height_cm = models.PositiveSmallIntegerField(null=True, blank=True)
    weight_kg = models.FloatField(null=True, blank=True)
    gender = models.CharField(max_length=10, blank=True)
    goal = models.CharField(max_length=50, blank=True)  # e.g., 'Fat Loss', 'Muscle Gain'
    experience_level = models.CharField(max_length=20, blank=True)  # Beginner/Intermediate/Advanced
    is_payment_approved = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username

class WorkoutPlan(models.Model):
    member = models.ForeignKey(MemberProfile, on_delete=models.CASCADE, related_name='workouts')
    title = models.CharField(max_length=120)
    content = models.TextField()  # AI-generated plan or manual
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.member.user.username} - {self.title}"

class DietPlan(models.Model):
    member = models.ForeignKey(MemberProfile, on_delete=models.CASCADE, related_name='diets')
    title = models.CharField(max_length=120)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.member.user.username} - {self.title}"

class ProgressEntry(models.Model):
    member = models.ForeignKey('MemberProfile', on_delete=models.CASCADE, related_name='progress_entries')
    date = models.DateField()
    weight_kg = models.FloatField(null=True, blank=True)
    body_fat_pct = models.FloatField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.member.user.username} - {self.date}"


class Progress(models.Model):
    member = models.ForeignKey(MemberProfile, on_delete=models.CASCADE, related_name='progress')
    date = models.DateField()
    weight_kg = models.FloatField(null=True, blank=True)
    body_fat_pct = models.FloatField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.member.user.username} - {self.date}"


class ProgressPhoto(models.Model):
    member = models.ForeignKey('MemberProfile', related_name='photos', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='progress_photos/')
    caption = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Photo of {self.member.user.username} - {self.created_at.date()}"


class Payment(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]
    member = models.ForeignKey(MemberProfile, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    tx_id = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.member.user.username} - {self.amount} - {self.status}"
