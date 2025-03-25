import os
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import MaxValueValidator,MinValueValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model




class Topic(models.Model):
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_admin', True)  # Fix: Add this


        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class UserAccount(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    username = models.CharField(unique=True,max_length=225)
    first_name = models.CharField(max_length=225)
    last_name = models.CharField(max_length=225)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    bio = models.TextField(null=True)
    avatar = models.ImageField(null=True,blank=True, default="avatar.svg")
    is_online = models.BooleanField(default=False)

    profile_rating = models.DecimalField(null=True,
        max_digits=3,
        decimal_places=1,
        validators=[
            MinValueValidator(1.0),
            MaxValueValidator(5.0)
        ]
    ) 
    upvotes = models.PositiveIntegerField(default=0)
    downvotes = models.PositiveIntegerField(default=0)
    interested_topics = models.ManyToManyField(Topic, related_name="interested_users", blank=True)





    groups = models.ManyToManyField(
        'auth.Group',
        related_name='user_account_set',  # Custom related name for 'groups'
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='user_account_permissions_set',  # Custom related name for 'user_permissions'
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
     





 # Get the custom user model

UserAccount = get_user_model() 

class Room(models.Model):
    host = models.ForeignKey(UserAccount, on_delete=models.SET_NULL, null=True, related_name="hosted_rooms")
    topic = models.ForeignKey(Topic, on_delete=models.SET_NULL, null=True)
    name = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    participants = models.ManyToManyField(UserAccount, related_name='joined_rooms', blank=True)
    room_video_call_id = models.CharField(max_length=255, blank=True, null=True)  # Video Call ID
    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)


    class Meta:
        ordering = ['-updated', '-created']

    def __str__(self):
        return f"{self.name}"
    #  (Host: {self.host.email if self.host else 'Deleted User'})


class Message(models.Model):
    user = models.ForeignKey(UserAccount, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="messages")
    body = models.TextField(blank=True,null=True)
    file = models.FileField(upload_to='files/',blank=True,null=True)
    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-updated', '-created']
    
    @property
    def filename(self):
        if self.file:
            return os.path.basename(self.file.name)
        else:
            return None
        
    @property
    def is_image(self):
        if self.file:
            return self.file.name.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp'))
        return False


    def __str__(self):
        if self.body:
            return f"Message from {self.user.email}: {self.body[:50]}..."
        elif self.file:
            return f"Message from {self.user.email}: {self.filename}"


class RoomFeedback(models.Model):
    VOTE_CHOICES = (
        (1, 'Upvote'),
        (-1, 'Downvote'),
    )

    user = models.ForeignKey(UserAccount, on_delete=models.CASCADE, related_name="room_feedbacks")
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="feedbacks")
    vote = models.IntegerField(choices=VOTE_CHOICES, null=True, blank=True)  # Either 1 (upvote) or -1 (downvote)
    feedback_text = models.TextField(null=True, blank=True)  # Optional feedback
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'room')  # Ensure one vote per user per room

    def __str__(self):
        return f"{self.user.email} -> {self.room.name} ({'Upvote' if self.vote == 1 else 'Downvote' if self.vote == -1 else 'No Vote'})"

