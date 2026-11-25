from django.urls import path

from universities import views

urlpatterns = [
    path("universities/", views.university_list, name="university_list"),
    path("universities/<int:pk>/", views.university_detail, name="university_detail"),
    path("courses/<int:pk>/", views.course_detail, name="course_detail"),
]
