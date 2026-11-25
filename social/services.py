from typing import Any

from accounts.models import User
from social.models import CourseFollow, UserFollow
from universities.models import Course


def user_follow_context(viewer: User, person: User) -> dict[str, Any]:
    return {
        "person": person,
        "is_following": UserFollow.objects.filter(follower=viewer, followed=person).exists(),
        "follower_count": UserFollow.objects.filter(followed=person).count(),
        "following_count": UserFollow.objects.filter(follower=person).count(),
    }


def course_follow_context(viewer: User, course: Course) -> dict[str, Any]:
    return {
        "course": course,
        "is_following": CourseFollow.objects.filter(user=viewer, course=course).exists(),
        "follower_count": CourseFollow.objects.filter(course=course).count(),
    }


def set_user_follow(viewer: User, person: User, *, follow: bool) -> None:
    if follow:
        UserFollow.objects.get_or_create(follower=viewer, followed=person)
    else:
        UserFollow.objects.filter(follower=viewer, followed=person).delete()


def set_course_follow(viewer: User, course: Course, *, follow: bool) -> None:
    if follow:
        CourseFollow.objects.get_or_create(user=viewer, course=course)
    else:
        CourseFollow.objects.filter(user=viewer, course=course).delete()
