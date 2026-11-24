import pytest
from django.core.exceptions import ValidationError
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from accounts.models import User
from tests.factories import (
    CourseFactory,
    FacultyFactory,
    UniversityFactory,
    UserFactory,
    professor,
)
from universities.models import University


@pytest.fixture
def uni() -> University:
    return UniversityFactory.create(name="Universiteti i Tiranës")


@pytest.fixture
def student(uni: University) -> User:
    return UserFactory.create(university=uni)


@pytest.mark.django_db
@pytest.mark.parametrize("name", ["university_list"])
def test_pages_require_login(client: Client, name: str) -> None:
    response = client.get(reverse(name))
    assert response.status_code == 302


@pytest.mark.django_db
def test_university_list_hides_pending_universities_of_others(
    client: Client, student: User
) -> None:
    UniversityFactory.create(name="Pending Elsewhere", status=University.Status.PENDING)
    UniversityFactory.create(name="Universiteti Politeknik")
    client.force_login(student)

    html = client.get(reverse("university_list")).content.decode()

    assert "Universiteti Politeknik" in html
    assert "Universiteti i Tiranës" in html
    assert "Pending Elsewhere" not in html


@pytest.mark.django_db
def test_members_can_see_their_own_pending_university(client: Client) -> None:
    uni = UniversityFactory.create(name="cit.edu.al", status=University.Status.PENDING)
    client.force_login(UserFactory.create(university=uni))

    response = client.get(reverse("university_detail", args=[uni.pk]))

    assert response.status_code == 200
    assert "Një administrator do ta konfirmojë" in response.content.decode()


@pytest.mark.django_db
def test_others_get_404_for_a_pending_university_and_its_courses(
    client: Client, student: User
) -> None:
    uni = UniversityFactory.create(status=University.Status.PENDING)
    course = CourseFactory.create(university=uni)
    client.force_login(student)

    assert client.get(reverse("university_detail", args=[uni.pk])).status_code == 404
    assert client.get(reverse("course_detail", args=[course.pk])).status_code == 404


@pytest.mark.django_db
def test_admins_see_pending_universities(client: Client) -> None:
    uni = UniversityFactory.create(status=University.Status.PENDING)
    client.force_login(UserFactory.create(role=User.Role.ADMIN))

    assert client.get(reverse("university_detail", args=[uni.pk])).status_code == 200


@pytest.mark.django_db
def test_university_page_lists_faculties_and_courses(
    client: Client, student: User, uni: University
) -> None:
    fac = FacultyFactory.create(university=uni, name="Fakulteti i Ekonomisë")
    CourseFactory.create(university=uni, faculty=fac, name="Mikroekonomi", code="EKO101")
    CourseFactory.create(university=uni, name="Gjuhë Angleze")  # no faculty
    client.force_login(student)

    html = client.get(reverse("university_detail", args=[uni.pk])).content.decode()

    assert "Fakulteti i Ekonomisë" in html
    assert "Mikroekonomi" in html
    assert "EKO101" in html
    assert "Lëndë të tjera" in html
    assert "Gjuhë Angleze" in html


@pytest.mark.django_db
def test_university_page_query_count_does_not_grow_with_faculties(
    client: Client, student: User, uni: University
) -> None:
    client.force_login(student)

    def count() -> int:
        with CaptureQueriesContext(connection) as ctx:
            client.get(reverse("university_detail", args=[uni.pk]))
        return len(ctx)

    fac = FacultyFactory.create(university=uni)
    CourseFactory.create(university=uni, faculty=fac)
    before = count()
    for _ in range(5):
        f = FacultyFactory.create(university=uni)
        CourseFactory.create_batch(3, university=uni, faculty=f)

    assert count() == before


@pytest.mark.django_db
def test_course_page_shows_professors_with_badge(client: Client, student: User) -> None:
    course = CourseFactory.create(university=student.university, name="Algoritme")
    prof = professor(display_name="Prof. Dritan Çela")
    course.professors.add(prof)
    client.force_login(student)

    html = client.get(reverse("course_detail", args=[course.pk])).content.decode()

    assert "Algoritme" in html
    assert "Prof. Dritan Çela" in html
    assert "Profesor i verifikuar" in html


@pytest.mark.django_db
def test_students_can_view_courses_of_other_active_universities(
    client: Client, student: User
) -> None:
    course = CourseFactory.create()  # another, active university
    client.force_login(student)

    assert client.get(reverse("course_detail", args=[course.pk])).status_code == 200


@pytest.mark.django_db
def test_course_faculty_must_belong_to_the_same_university() -> None:
    course = CourseFactory.build(
        university=UniversityFactory.create(), faculty=FacultyFactory.create()
    )

    with pytest.raises(ValidationError, match="faculty"):
        course.full_clean()


@pytest.mark.django_db
def test_course_professor_choices_are_only_verified_professors() -> None:
    from django.forms import modelform_factory

    from universities.models import Course

    student = UserFactory.create()
    pending = UserFactory.create(
        role=User.Role.PROFESSOR, professor_status=User.ProfessorStatus.PENDING
    )
    verified = professor()
    field = modelform_factory(Course, fields=("professors",))().fields["professors"]

    choices = set(field.queryset)  # type: ignore[attr-defined]
    assert verified in choices
    assert student not in choices
    assert pending not in choices
