from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.http.response import HttpResponseBase
from django.shortcuts import render

from core.auth import AuthedRequest, verified_required
from posts.queries import feed_posts
from social.models import CourseFollow, UserFollow

PAGE_SIZE = 20


def home(request: HttpRequest) -> HttpResponseBase:
    if request.user.is_authenticated:
        return feed(request)
    return render(request, "core/home.html")


@verified_required
def feed(request: AuthedRequest) -> HttpResponse:
    user = request.user
    followed_users = UserFollow.objects.filter(follower=user).values("followed")
    followed_courses = CourseFollow.objects.filter(user=user).values("course")
    follows_anything = (
        UserFollow.objects.filter(follower=user).exists()
        or CourseFollow.objects.filter(user=user).exists()
    )
    tab = request.GET.get("tab") or ("following" if follows_anything else "university")
    if tab not in {"following", "university"}:
        tab = "university"

    posts = feed_posts(user)
    if tab == "following":
        # Still inside visible_to(): following someone never reveals posts you couldn't see.
        posts = posts.filter(
            Q(author__in=followed_users) | Q(course__in=followed_courses) | Q(author=user)
        )
    page = Paginator(posts, PAGE_SIZE).get_page(request.GET.get("page"))
    return render(
        request,
        "core/feed.html",
        {"page": page, "tab": tab, "follows_anything": follows_anything},
    )
