from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.models import User
from core.auth import AuthedRequest, verified_required
from social import services
from universities.models import Course, University


def _wants_follow(request: AuthedRequest) -> bool:
    # Explicit state instead of a toggle: a double click or a retry can't flip it back.
    return request.POST.get("follow") == "1"


def _is_htmx(request: AuthedRequest) -> bool:
    return request.headers.get("HX-Request") == "true"


@require_POST
@verified_required
def follow_user(request: AuthedRequest, pk: int) -> HttpResponse:
    person = get_object_or_404(User.objects.filter(is_active=True), pk=pk)
    if person == request.user:
        raise Http404
    services.set_user_follow(request.user, person, follow=_wants_follow(request))
    if _is_htmx(request):
        context = services.user_follow_context(request.user, person)
        return render(request, "social/_follow_user.html", context)
    return redirect("profile", pk=person.pk)


@require_POST
@verified_required
def follow_course(request: AuthedRequest, pk: int) -> HttpResponse:
    course = get_object_or_404(
        Course.objects.filter(university__in=University.objects.visible_to(request.user)), pk=pk
    )
    services.set_course_follow(request.user, course, follow=_wants_follow(request))
    if _is_htmx(request):
        context = services.course_follow_context(request.user, course)
        return render(request, "social/_follow_course.html", context)
    return redirect("course_detail", pk=course.pk)


@verified_required
def followers(request: AuthedRequest, pk: int) -> HttpResponse:
    person = get_object_or_404(User.objects.filter(is_active=True), pk=pk)
    people = User.objects.filter(is_active=True, following_links__followed=person).select_related(
        "university"
    )
    return render(
        request, "social/people.html", {"person": person, "people": people, "kind": "followers"}
    )


@verified_required
def following(request: AuthedRequest, pk: int) -> HttpResponse:
    person = get_object_or_404(User.objects.filter(is_active=True), pk=pk)
    people = User.objects.filter(is_active=True, follower_links__follower=person).select_related(
        "university"
    )
    courses = (
        Course.objects.filter(follows__user=person)
        .filter(university__in=University.objects.visible_to(request.user))
        .select_related("university")
    )
    return render(
        request,
        "social/people.html",
        {"person": person, "people": people, "courses": courses, "kind": "following"},
    )
