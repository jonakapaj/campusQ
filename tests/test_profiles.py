import pytest
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from accounts.models import User
from tests.factories import FacultyFactory, UniversityFactory, UserFactory


@pytest.fixture
def ana() -> User:
    uni = UniversityFactory.create(name="Universiteti i Tiranës")
    return UserFactory.create(
        display_name="Ëngjëll Çela",
        university=uni,
        faculty=FacultyFactory.create(university=uni, name="Fakulteti i Shkencave"),
        field_of_study="Informatikë",
        year=2,
        bio="Më pëlqen matematika.",
    )


@pytest.mark.django_db
def test_profile_requires_login(client: Client, ana: User) -> None:
    response = client.get(reverse("profile", args=[ana.pk]))

    assert response.status_code == 302
    assert response["Location"].startswith(reverse("account_login"))


@pytest.mark.django_db
def test_unverified_session_cannot_see_profiles(client: Client, ana: User) -> None:
    client.force_login(UserFactory.create(verified=False))

    response = client.get(reverse("profile", args=[ana.pk]))

    assert response.status_code == 302
    assert response["Location"].startswith(reverse("account_email_verification_sent"))


@pytest.mark.django_db
def test_profile_shows_details_with_albanian_characters(client: Client, ana: User) -> None:
    client.force_login(UserFactory.create())

    html = client.get(reverse("profile", args=[ana.pk])).content.decode()

    assert "Ëngjëll Çela" in html
    assert "Universiteti i Tiranës" in html
    assert "Fakulteti i Shkencave" in html
    assert "Informatikë" in html
    assert "Viti 2" in html
    assert "Më pëlqen matematika." in html
    assert "ËÇ" in html  # initials avatar
    assert "Ndrysho profilin" not in html  # not your own profile


@pytest.mark.django_db
def test_students_of_other_universities_can_see_profiles(client: Client, ana: User) -> None:
    client.force_login(UserFactory.create(university=UniversityFactory.create()))

    assert client.get(reverse("profile", args=[ana.pk])).status_code == 200


@pytest.mark.django_db
def test_suspended_users_profile_is_hidden(client: Client, ana: User) -> None:
    ana.is_active = False
    ana.save()
    client.force_login(UserFactory.create())

    assert client.get(reverse("profile", args=[ana.pk])).status_code == 404


@pytest.mark.django_db
def test_profile_page_is_one_query_for_the_person(client: Client, ana: User) -> None:
    client.force_login(UserFactory.create())
    client.get(reverse("profile", args=[ana.pk]))  # warm up session/auth queries

    with CaptureQueriesContext(connection) as ctx:
        client.get(reverse("profile", args=[ana.pk]))

    person_queries = [q for q in ctx.captured_queries if '"universities_faculty"' in q["sql"]]
    assert len(person_queries) == 1  # joined, not fetched lazily


@pytest.mark.django_db
def test_user_can_edit_own_profile(client: Client, ana: User) -> None:
    client.force_login(ana)
    other_faculty = FacultyFactory.create(university=ana.university, name="Fakulteti Juridik")

    response = client.post(
        reverse("profile_edit"),
        {
            "display_name": "  Ëngjëll   Çela ",
            "faculty": other_faculty.pk,
            "field_of_study": "Drejtësi",
            "year": 3,
            "bio": "Përshëndetje!",
        },
    )

    assert response.status_code == 302
    ana.refresh_from_db()
    assert ana.display_name == "Ëngjëll Çela"
    assert ana.faculty == other_faculty
    assert ana.field_of_study == "Drejtësi"
    assert ana.year == 3


@pytest.mark.django_db
def test_cannot_pick_a_faculty_of_another_university(client: Client, ana: User) -> None:
    client.force_login(ana)
    foreign = FacultyFactory.create()  # different university

    response = client.post(reverse("profile_edit"), {"display_name": "Ana", "faculty": foreign.pk})

    assert response.status_code == 200  # form re-rendered with an error
    ana.refresh_from_db()
    assert ana.faculty != foreign


@pytest.mark.django_db
def test_edit_cannot_change_role_email_university_or_staff(client: Client, ana: User) -> None:
    client.force_login(ana)
    uni = ana.university

    client.post(
        reverse("profile_edit"),
        {
            "display_name": "Ana",
            "role": "ADMIN",
            "professor_status": "VERIFIED",
            "email": "evil@gmail.com",
            "university": UniversityFactory.create().pk,
            "is_staff": "on",
            "is_superuser": "on",
        },
    )

    ana.refresh_from_db()
    assert ana.role == User.Role.STUDENT
    assert ana.professor_status == User.ProfessorStatus.NONE
    assert ana.email.endswith("@unitir.edu.al")
    assert ana.university == uni
    assert not ana.is_staff
    assert not ana.is_superuser
    assert not ana.is_platform_admin


@pytest.mark.django_db
@pytest.mark.parametrize("year", [0, 7, -1])
def test_year_out_of_range_is_rejected(client: Client, ana: User, year: int) -> None:
    client.force_login(ana)

    response = client.post(reverse("profile_edit"), {"display_name": "Ana", "year": year})

    assert response.status_code == 200
    ana.refresh_from_db()
    assert ana.year == 2


@pytest.mark.django_db
def test_bio_is_capped_at_500_characters(client: Client, ana: User) -> None:
    client.force_login(ana)

    client.post(reverse("profile_edit"), {"display_name": "Ana", "bio": "x" * 501})

    ana.refresh_from_db()
    assert ana.bio == "Më pëlqen matematika."


@pytest.mark.django_db
def test_bio_is_escaped(client: Client, ana: User) -> None:
    ana.bio = "<script>alert(1)</script>"
    ana.save()
    client.force_login(UserFactory.create())

    html = client.get(reverse("profile", args=[ana.pk])).content.decode()

    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


@pytest.mark.django_db
def test_edit_profile_requires_login(client: Client) -> None:
    response = client.post(reverse("profile_edit"), {"display_name": "X"})

    assert response.status_code == 302
    assert response["Location"].startswith(reverse("account_login"))


@pytest.mark.parametrize(
    ("name", "initials"),
    [("Ëngjëll Çela", "ËÇ"), ("ana", "A"), ("Ana Maria Hoxha", "AM"), ("", "?")],
)
def test_initials(name: str, initials: str) -> None:
    assert User(display_name=name, email="").initials == initials


@pytest.mark.django_db
def test_platform_admin_requires_admin_role_or_superuser() -> None:
    assert not UserFactory.create().is_platform_admin
    assert UserFactory.create(role=User.Role.ADMIN).is_platform_admin
    assert not UserFactory.create(role=User.Role.ADMIN, is_active=False).is_platform_admin
    assert User.objects.create_superuser("r@x.edu.al", "pw", display_name="R").is_platform_admin
