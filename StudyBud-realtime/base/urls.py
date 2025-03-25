from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.loginPage, name="login"),
    path('logout/', views.logoutUser, name="logout"),
    path('register/', views.registerPage, name="register"),

    path('', views.home, name="home"),
    path('room/<str:pk>/', views.room, name="room"),
    path('profile/<str:pk>/', views.userProfile, name="user-profile"),

    path('create-room/', views.createRoom, name="create-room"),
    path('update-room/<str:pk>/', views.updateRoom, name="update-room"),
    path('delete-room/<str:pk>/', views.deleteRoom, name="delete-room"),
    path('delete-message/<str:pk>/', views.deleteMessage, name="delete-message"),

    path('update-user/', views.updateUser, name="update-user"),

    path('topics/', views.topicsPage, name="topics"),
    path('activity/', views.activityPage, name="activity"),
    path('fileupload/<str:room_name>/', views.file_upload, name='file-upload'),
    path("room/<int:room_id>/vote/<str:vote_type>/", views.vote_room, name="vote-room"),

    path("start-meeting/<str:room_id>/", views.start_meeting, name="start-meeting"),
    path("join-meeting/<str:room_id>/", views.join_meeting, name="join-meeting"),
    path("video-call/<str:room_id>/", views.video_call, name="video_call"),
    path("stop-meeting/<str:room_id>/", views.stop_meeting, name="stop-meeting"),

    path("summarize-room/<int:room_id>/", views.summarize_room, name="summarize-room"),



]
