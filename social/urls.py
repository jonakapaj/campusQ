from django.urls import path

from social import views

urlpatterns = [
    path("u/<int:pk>/follow/", views.follow_user, name="follow_user"),
    path("u/<int:pk>/followers/", views.followers, name="followers"),
    path("u/<int:pk>/following/", views.following, name="following"),
    path("courses/<int:pk>/follow/", views.follow_course, name="follow_course"),
]
