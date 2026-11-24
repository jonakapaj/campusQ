from django.db.models import Count, Prefetch
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render

from core.auth import AuthedRequest, verified_required
from universities.models import Course, Faculty, University


@verified_required
def university_list(request: AuthedRequest) -> HttpResponse:
    universities = (
        University.objects.visible_to(request.user)
        .annotate(
            member_count=Count("members", distinct=True),
            course_count=Count("courses", distinct=True),
        )
        .order_by("name")
    )
    return render(request, "universities/list.html", {"universities": universities})


@verified_required
def university_detail(request: AuthedRequest, pk: int) -> HttpResponse:
    university = get_object_or_404(University.objects.visible_to(request.user), pk=pk)
    # Two queries for every faculty and its courses, instead of one per faculty.
    faculties = Faculty.objects.filter(university=university).prefetch_related(
        Prefetch("courses", queryset=Course.objects.order_by("name"))
    )
    unassigned = Course.objects.filter(university=university, faculty__isnull=True)
    return render(
        request,
        "universities/detail.html",
        {
            "university": university,
            "faculties": faculties,
            "unassigned_courses": unassigned,
            "member_count": university.members.filter(is_active=True).count(),
        },
    )


@verified_required
def course_detail(request: AuthedRequest, pk: int) -> HttpResponse:
    course = get_object_or_404(
        Course.objects.filter(
            university__in=University.objects.visible_to(request.user)
        ).select_related("university", "faculty"),
        pk=pk,
    )
    professors = course.professors.filter(is_active=True).order_by("display_name")
    return render(request, "universities/course.html", {"course": course, "professors": professors})
