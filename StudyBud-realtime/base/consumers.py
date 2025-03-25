import json
import re
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from .models import Message, Room
from django.contrib.auth import get_user_model

User = get_user_model()

# Dictionary to store online users in each room
online_users = {}

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """Handles WebSocket connection"""
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f"chat_{re.sub(r'[^a-zA-Z0-9_.-]', '_', self.room_name)}"
        self.username = self.scope["user"].username  # Get the username

        # Join the room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        # Add user to online list
        if self.room_group_name not in online_users:
            online_users[self.room_group_name] = set()
        online_users[self.room_group_name].add(self.username)

        # Notify all users about updated online count
        await self.broadcast_online_users()

    async def disconnect(self, close_code):
        """Handles WebSocket disconnection"""
        if self.room_group_name in online_users:
            online_users[self.room_group_name].discard(self.username)

            # Notify others about updated online users list
            await self.broadcast_online_users()

        # Leave the room group
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        """Handles incoming messages"""
        data = json.loads(text_data)
        message = data.get('message')
        username = data.get('username')
        room_name = data.get('room')

        if not all([message, username, room_name]):
            await self.send(text_data=json.dumps({'error': 'Invalid data'}))
            return

        # Fetch room and user
        room = await self.get_room(room_name)
        user = await self.get_user(username)

        if room and user:
            await self.save_message(user, room, message)

            # Send message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                    'username': username
                }
            )
        else:
            await self.send(text_data=json.dumps({'error': 'Invalid user or room'}))
        

        if data.get("type") == "video_status":
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "update_video_status",
                    "status": data["status"],
                    "room_id": data["room_id"]
                }
            )

    async def update_video_status(self, event):
        await self.send(text_data=json.dumps({
            "type": "video_status",
            "status": event["status"],
            "room_id": event["room_id"]
        }))

    async def chat_message(self, event):
        """Sends chat messages to the WebSocket"""
        message = event['message']
        username = event['username']

        await self.send(text_data=json.dumps({
            'message': message,
            'username': username
        }))

    async def message_handler(self, event):
        """Handles file upload events in the WebSocket"""
        file_url = event.get('file_url')
        username = event.get('username')
        filename = event.get('filename', 'Download File')
        is_image = event.get('is_image', False)  # Track if file is an image

        await self.send(text_data=json.dumps({
            'type': 'file_upload',
            'file_url': file_url,
            'username': username,
            'filename': filename,
            'is_image': is_image  # Include is_image flag
        }))

    async def broadcast_online_users(self):
        """Broadcasts updated online users list"""
        if self.room_group_name in online_users:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "update_online_users",
                    "online_users": list(online_users[self.room_group_name])
                }
            )

    async def update_online_users(self, event):
        """Sends online users list to the WebSocket"""
        await self.send(text_data=json.dumps({
            "type": "online_users",
            "online_users": event["online_users"]
        }))

    @sync_to_async
    def save_message(self, user, room, message):
        """Saves message to database"""
        return Message.objects.create(user=user, room=room, body=message)

    @sync_to_async
    def get_room(self, room_name):
        """Fetches room instance"""
        return Room.objects.filter(name=room_name).first()

    @sync_to_async
    def get_user(self, username):
        """Fetches user instance"""
        return User.objects.filter(username=username).first()

    
