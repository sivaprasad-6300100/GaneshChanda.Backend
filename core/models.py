import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from datetime import timedelta


def generate_committee_code():
    return uuid.uuid4().hex[:8].upper()


class Committee(models.Model):
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=8, unique=True, default=generate_committee_code)
    is_paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.code})"


class MemberManager(BaseUserManager):
    def create_user(self, phone, name, committee, password=None):
        if not phone:
            raise ValueError('Phone number is required')
        if not name:
            raise ValueError('Name is required')
        if not committee:
            raise ValueError('Committee is required')
        user = self.model(phone=phone, name=name, committee=committee)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, name, password=None, committee=None):
        if committee is None:
            committee, _ = Committee.objects.get_or_create(name='Admin')
        user = self.create_user(phone, name, committee, password)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user


def member_profile_pic_path(instance, filename):
    ext = filename.split('.')[-1]
    return f'profile_pics/{instance.id}.{ext}'


class Member(AbstractBaseUser, PermissionsMixin):
    committee = models.ForeignKey(Committee, on_delete=models.CASCADE, related_name='members')
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=10, unique=True)
    is_admin = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    profile_picture = models.ImageField(upload_to=member_profile_pic_path, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = MemberManager()

    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = ['name']

    def __str__(self):
        return f"{self.name} - {self.committee.name}"


class Entry(models.Model):
    committee = models.ForeignKey(Committee, on_delete=models.CASCADE, related_name='entries')
    logged_by = models.ForeignKey(Member, on_delete=models.SET_NULL, null=True, related_name='logged_entries')
    contributor_name = models.CharField(max_length=150)
    mobile = models.CharField(max_length=10)
    amount = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.contributor_name} - Rs.{self.amount}"


class OtpVerification(models.Model):
    phone = models.CharField(max_length=10, unique=True)
    verification_id = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_fresh(self):
        # OTP good for 10 minutes, matches typical Message Central expiry
        return timezone.now() - self.created_at < timedelta(minutes=10)

    def __str__(self):
        return f"OTP pending for {self.phone}"






class Expense(models.Model):
    CATEGORY_CHOICES = [
    ('decoration', 'Decoration'),
    ('pandal', 'Pandal / Mandapam'),
    ('lighting', 'Lighting & Electrical'),
    ('sound', 'Sound System'),
    ('music', 'Music / DJ / Drums'),
    ('idol', 'Idol / Statue'),
    ('pooja', 'Pooja Materials'),
    ('priest', 'Priest / Purohit'),
    ('prasadam', 'Prasadam / Food'),
    ('flowers', 'Flowers & Garlands'),
    ('transport', 'Transport / Vehicle'),
    ('printing', 'Printing & Flex'),
    ('publicity', 'Publicity / Advertising'),
    ('water', 'Water / Drinking Water'),
    ('cleaning', 'Cleaning & Sanitation'),
    ('security', 'Security'),
    ('permissions', 'Permissions / Government Fees'),
    ('misc', 'Miscellaneous'),
]

    committee = models.ForeignKey(Committee, on_delete=models.CASCADE, related_name='expenses')
    logged_by = models.ForeignKey(Member, on_delete=models.SET_NULL, null=True, related_name='logged_expenses')
    title = models.CharField(max_length=150)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='misc')
    amount = models.PositiveIntegerField()
    notes = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - Rs.{self.amount}"