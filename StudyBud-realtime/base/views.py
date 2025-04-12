import random
import re
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from asgiref.sync import async_to_sync
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.contrib.auth import authenticate, login, logout
from .models import Room, Topic, Message, UserAccount,RoomFeedback
from .forms import  RoomForm,UserForm,MyUserCreationForm
from channels.layers import get_channel_layer

from django.views.decorators.csrf import csrf_exempt
from google import genai


# Initialize Gemini API
API_KEY = "AIzaSyD_7I7myoDeXiJoguxW1ScDfHl6U11jZOY"
genai_client = genai.Client(api_key=API_KEY)




# def home(request):
#     return HttpResponse("Hello, World")
# # rooms = [
# #     {'id': 1, 'name': 'Lets learn python!'},
# #     {'id': 2, 'name': 'Design with me'},
# #     {'id': 3, 'name': 'Frontend developers'},
# # ]


def loginPage(request):
    page = 'login'
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        email = request.POST.get('email').lower()
        password = request.POST.get('password')

        try:
            user = UserAccount.objects.get(email=email)
        except:
            messages.error(request, 'User does not exist')

        user = authenticate(request, email=email, password=password)

        if user is not None:
            login(request, user)
            user.is_online = True
            user.save()
            return redirect('home')
        else:
            messages.error(request, 'Username OR password does not exit')

    context = {'page': page}
    return render(request, 'base/login_register.html', context)


def logoutUser(request):
    user = UserAccount.objects.get(email=request.user.email)
    logout(request)
    user.is_online = False
    user.save()
    return redirect('home')


def registerPage(request):
    form = MyUserCreationForm()

    if request.method == 'POST':
        form = MyUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.username = user.username.lower()
            user.save()
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, form.errors)

    return render(request, 'base/login_register.html', {'form': form})


def home(request):
    q = request.GET.get('q') if request.GET.get('q') != None else ''

    rooms = Room.objects.filter(
        Q(topic__name__icontains=q) |
        Q(name__icontains=q) |
        Q(description__icontains=q)
    )

    topics = Topic.objects.all()[0:5]
    room_count = rooms.count()
    room_messages = Message.objects.filter(
        Q(room__topic__name__icontains=q))[0:3]
    

    for room in rooms:
        room.upvote_count = room.feedbacks.filter(vote=1).count()
        room.downvote_count = room.feedbacks.filter(vote=-1).count()

    context = {'rooms': rooms, 'topics': topics,
               'room_count': room_count, 'room_messages': room_messages}
    return render(request, 'base/home.html', context)


@login_required
def room(request, pk):
    room = get_object_or_404(Room, id=pk)
    room_messages = room.messages.all().select_related('user').order_by('-created')[:50]  # Fetch latest 50 messages
    room.participants.add(request.user)
    participants = room.participants.all()


    # if request.method == 'POST':
    #     body = request.POST.get('body', '').strip()
    #     if body:  # Ensure message is not empty
    #         message = Message.objects.create(
    #             user=request.user,
    #             room=room,
    #             body=body
    #         )
    #         return redirect('room', pk=room.id)

    context = {'room': room, 'room_messages': reversed(room_messages), 'participants': participants}
    return render(request, 'base/room.html', context)

@login_required
def file_upload(request, room_name):
    if request.method == 'POST' and request.FILES:
        file = request.FILES['file']
        is_image = file.content_type.startswith('image/')
        room = get_object_or_404(Room, name=room_name)

        message = Message.objects.create(
            file=file,
            user=request.user,
            room=room,
        )

        channel_layer = get_channel_layer()
        filename = file.name  # Ensure filename is always available

        event = {
            'type': 'message_handler',
            'username': request.user.username,
            'file_url': message.file.url,
            'filename': filename,
            'is_image': is_image
        }
        room_group_name = f"chat_{re.sub(r'[^a-zA-Z0-9_.-]', '_', room_name)}"
        async_to_sync(channel_layer.group_send)(room_group_name, event)

        return JsonResponse({'file_url': message.file.url, 'username': request.user.username, 'is_image': is_image})
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


def userProfile(request, pk):
    user = get_object_or_404(UserAccount, id=pk)

    # Get rooms where the user is either host or participant
    rooms = user.hosted_rooms.all() 

    # Get messages sent by the user (optimized with select_related for room data)
    room_messages = Message.objects.filter(user=user).select_related('room')

    # Get all topics (assuming needed for frontend filters or display)
    topics = Topic.objects.all()

    context = {
        'user': user,
        'rooms': rooms,
        'room_messages': room_messages,
        'topics': topics
    }

    return render(request, 'base/profile.html', context)


@login_required(login_url='login')
def createRoom(request):
    form = RoomForm()
    topics = Topic.objects.all()
    if request.method == 'POST':
        topic_name = request.POST.get('topic')
        topic, created = Topic.objects.get_or_create(name=topic_name)

        Room.objects.create(
            host=request.user,
            topic=topic,
            name=request.POST.get('name'),
            description=request.POST.get('description'),
        )
        return redirect('home')

    context = {'form': form, 'topics': topics}
    return render(request, 'base/room_form.html', context)


@login_required(login_url='login')
def updateRoom(request, pk):
    room = Room.objects.get(id=pk)
    form = RoomForm(instance=room)
    topics = Topic.objects.all()
    if request.user != room.host:
        return HttpResponse('Your are not allowed here!!')

    if request.method == 'POST':
        topic_name = request.POST.get('topic')
        topic, created = Topic.objects.get_or_create(name=topic_name)
        room.name = request.POST.get('name')
        room.topic = topic
        room.description = request.POST.get('description')
        room.save()
        return redirect('home')

    context = {'form': form, 'topics': topics, 'room': room}
    return render(request, 'base/room_form.html', context)


@login_required(login_url='login')
def deleteRoom(request, pk):
    room = Room.objects.get(id=pk)

    if request.user != room.host:
        return HttpResponse('Your are not allowed here!!')

    if request.method == 'POST':
        room.delete()
        return redirect('home')
    return render(request, 'base/delete.html', {'obj': room})


@login_required(login_url='login')
def deleteMessage(request, pk):
    message = Message.objects.get(id=pk)

    if request.user != message.user:
        return HttpResponse('Your are not allowed here!!')

    if request.method == 'POST':
        message.delete()
        return redirect('home')
    return render(request, 'base/delete.html', {'obj': message})


@login_required(login_url='login')
def updateUser(request):
    user = request.user
    form = UserForm(instance=user)

    if request.method == 'POST':
        form = UserForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            return redirect('user-profile', pk=user.id)

    return render(request, 'base/update-user.html', {'form': form})


def topicsPage(request):
    q = request.GET.get('q') if request.GET.get('q') != None else ''
    topics = Topic.objects.filter(name__icontains=q)
    return render(request, 'base/topics.html', {'topics': topics})


def activityPage(request):
    room_messages = Message.objects.all()
    return render(request, 'base/activity.html', {'room_messages': room_messages})



@login_required
def vote_room(request, room_id, vote_type):
    room = get_object_or_404(Room, id=room_id)
    vote_value = 1 if vote_type == "upvote" else -1

    # Try to get or create the feedback
    feedback, created = RoomFeedback.objects.get_or_create(user=request.user, room=room, defaults={"vote": vote_value})

    if not created:  
        if feedback.vote == vote_value:
            feedback.delete()
            return JsonResponse({"message": "Vote removed", "total_votes": room.feedbacks.count()}, status=200)
        else:
            feedback.vote = vote_value
            feedback.save()
            return JsonResponse({"message": "Vote updated", "total_votes": room.feedbacks.count()}, status=200)

    return JsonResponse({"message": "Vote recorded", "total_votes": room.feedbacks.count()}, status=200)



def video_call(request, room_id):
    return render(request, "base/video_call.html", {"room_id": room_id})

def start_meeting(request, room_id):
    room = get_object_or_404(Room, id=room_id)

    if request.user != room.host:
        return redirect("home")  # Restrict non-host users

    # Generate a unique meeting ID if not set
    if not room.room_video_call_id:
        room.room_video_call_id = str(random.randint(100000, 999999))  # Random 6-digit ID
        room.save()

    return redirect("video_call", room_id=room.room_video_call_id)

def join_meeting(request, room_id):
    room = get_object_or_404(Room, id=room_id)

    if not room.room_video_call_id:
        return redirect("home")  # Redirect if the meeting is not live

    return redirect("video_call", room_id=room.room_video_call_id)


@login_required
def stop_meeting(request, room_id):
    room = get_object_or_404(Room, id=room_id)

    # Ensure only the host can stop the meeting
    if request.user == room.host:
        room.room_video_call_id = None  # Clear meeting ID
        room.save()
        return redirect("room", pk=room_id)
    
    return JsonResponse({"success": False, "error": "You are not authorized!"}, status=403)





@csrf_exempt
def summarize_room(request, room_id):
    if request.method == "POST":
        room = get_object_or_404(Room, id=room_id)

        # Fetch room details
        room_title = room.name
        room_topic = room.topic.name if room.topic else "No specific topic"
        room_host = room.host.username if room.host else "Unknown Host"
        participant_count = room.participants.count()

        # Fetch latest 1000 messages (Only Text Messages)
        messages = Message.objects.filter(room=room, body__isnull=False).order_by("-created")[:1000]
        messages_text = "\n".join([f"{msg.user.username}: {msg.body}" for msg in messages])

        # Create AI input prompt
        ai_prompt = f"""
        Room Summary:
        - Room Title: {room_title}
        - Topic: {room_topic}
        - Host: {room_host}
        - Participants Count: {participant_count}

        Messages: 
        {messages_text if messages_text else 'No messages available.'}

        Summarize this discussion effectively.
        """

        # Send to Google Gemini API
        response = genai_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=ai_prompt,
        )

        # Get response
        summary = response.text if response.text else "Failed to generate summary."

        return JsonResponse({"summary": summary})
    
    return JsonResponse({"error": "Invalid request method."}, status=400)
