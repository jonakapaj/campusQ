from django.urls import path

from accounts import views

urlpatterns = [
    path("u/<int:pk>/", views.profile, name="profile"),
    path("settings/profile/", views.profile_edit, name="profile_edit"),
]
