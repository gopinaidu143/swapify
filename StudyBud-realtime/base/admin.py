from django.contrib import admin

# Register your models here.

from .models import Room, Topic, Message, UserAccount

admin.site.register(UserAccount)
admin.site.register(Room)
admin.site.register(Topic)
admin.site.register(Message)
