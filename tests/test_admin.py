import pytest
from django.test import Client
from django.urls import reverse

from accounts.models import User
from tests.factories import UniversityDomainFactory, UniversityFactory, UserFactory
from universities.models import University

ADMIN_PAGES = [
    "admin:universities_university_changelist",
    "admin:universities_universitydomain_changelist",
    "admin:accounts_user_changelist",
    "admin:accounts_user_add",
]


@pytest.mark.django_db
@pytest.mark.parametrize("page", ADMIN_PAGES)
def test_students_cannot_open_the_admin(client: Client, page: str) -> None:
    client.force_login(UserFactory.create())

    response = client.get(reverse(page))

    assert response.status_code == 302
    assert reverse("admin:login") in response["Location"]


@pytest.fixture
def admin_client_(client: Client) -> Client:
    admin = User.objects.create_superuser("root@unitir.edu.al", "pw", display_name="Root")
    client.force_login(admin)
    return client


@pytest.mark.django_db
@pytest.mark.parametrize("page", ADMIN_PAGES)
def test_admin_pages_load(admin_client_: Client, page: str) -> None:
    assert admin_client_.get(reverse(page)).status_code == 200


@pytest.mark.django_db
def test_university_list_query_count_does_not_grow_with_rows(
    admin_client_: Client, django_assert_max_num_queries: object
) -> None:
    for _ in range(10):
        domain = UniversityDomainFactory.create()
        UserFactory.create(university=domain.university)
    url = reverse("admin:universities_university_changelist")

    with django_assert_max_num_queries(10):  # type: ignore[operator]
        admin_client_.get(url)


@pytest.mark.django_db
def test_pending_subdomain_shows_its_parent_as_a_hint(admin_client_: Client) -> None:
    UniversityDomainFactory.create(
        domain="unitir.edu.al", university__name="Universiteti i Tiranës"
    )
    pending = UniversityDomainFactory.create(
        domain="students.unitir.edu.al", university__status=University.Status.PENDING
    ).university

    html = admin_client_.get(
        reverse("admin:universities_university_change", args=[pending.pk])
    ).content.decode()

    assert "Universiteti i Tiranës (unitir.edu.al)" in html


@pytest.mark.django_db
def test_activate_action(admin_client_: Client) -> None:
    pending = UniversityFactory.create(status=University.Status.PENDING)

    admin_client_.post(
        reverse("admin:universities_university_changelist"),
        {"action": "activate", "_selected_action": [pending.pk]},
    )

    pending.refresh_from_db()
    assert pending.status == University.Status.ACTIVE
