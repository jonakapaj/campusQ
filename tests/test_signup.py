import re

import pytest
from allauth.account.models import EmailAddress
from django.conf import settings
from django.core import mail
from django.test import Client
from django.urls import reverse

from accounts.models import User
from tests.factories import UniversityDomainFactory, UserFactory
from universities.models import University

PASSWORD = "Ndryshe-2026-fjalekalim"


def signup(client: Client, email: str, **extra: str) -> str:
    data = {
        "display_name": "Ana Hoxha",
        "email": email,
        "password1": PASSWORD,
        "password2": PASSWORD,
        **extra,
    }
    return client.post(reverse("account_signup"), data, follow=True).content.decode()


def confirmation_url() -> str:
    body = str(mail.outbox[-1].body)
    match = re.search(r"https?://[^\s]+/accounts/confirm-email/[^\s]+/", body)
    assert match, body
    return match.group(0).split("testserver", 1)[1]


def confirm(client: Client) -> None:
    client.post(confirmation_url(), follow=True)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "email", ["ana@gmail.com", "ana@fake-edu.al", "ana@edu.al.evil.com", "ana@edu.al"]
)
def test_signup_rejects_non_university_email(client: Client, email: str) -> None:
    html = signup(client, email)

    assert not User.objects.exists()
    assert "Përdor adresën e emailit të universitetit" in html  # shown in Albanian
    assert not mail.outbox


@pytest.mark.django_db
def test_signup_sends_a_verification_email_and_does_not_sign_in(client: Client) -> None:
    html = signup(client, "Ana@UniTir.edu.al")

    user = User.objects.get()
    assert user.email == "ana@unitir.edu.al"
    assert user.display_name == "Ana Hoxha"
    assert not EmailAddress.objects.get(user=user).verified
    assert len(mail.outbox) == 1
    assert "Kontrollo emailin" in html
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
def test_unverified_user_cannot_sign_in(client: Client) -> None:
    UserFactory.create(email="ana@unitir.edu.al", verified=False)

    response = client.post(
        reverse("account_login"),
        {"login": "ana@unitir.edu.al", "password": "correct-horse-battery"},
        follow=True,
    )

    assert "_auth_user_id" not in client.session
    assert response.redirect_chain[-1][0] == reverse("account_email_verification_sent")
    assert len(mail.outbox) == 1  # a fresh link is sent


@pytest.mark.django_db
def test_verified_user_can_sign_in(client: Client) -> None:
    user = UserFactory.create(email="ana@unitir.edu.al")

    client.post(
        reverse("account_login"),
        {"login": "ANA@unitir.edu.al", "password": "correct-horse-battery"},
    )

    assert client.session["_auth_user_id"] == str(user.pk)


@pytest.mark.django_db
def test_confirming_links_a_known_university_and_signs_in(client: Client) -> None:
    domain = UniversityDomainFactory.create(domain="unitir.edu.al")
    signup(client, "ana@unitir.edu.al")

    confirm(client)

    user = User.objects.get()
    assert EmailAddress.objects.get(user=user).verified
    assert user.university == domain.university
    assert client.session["_auth_user_id"] == str(user.pk)


@pytest.mark.django_db
def test_unknown_domain_creates_a_pending_university_only_after_verification(
    client: Client,
) -> None:
    signup(client, "ana@new-uni.edu.al")
    assert not University.objects.exists()

    confirm(client)

    university = University.objects.get()
    assert university.status == University.Status.PENDING
    assert User.objects.get().university == university


@pytest.mark.django_db
def test_allowlisted_domain_can_sign_up(client: Client) -> None:
    domain = UniversityDomainFactory.create(domain="upt.al")
    signup(client, "prof@upt.al")

    confirm(client)

    assert User.objects.get().university == domain.university


@pytest.mark.django_db
def test_confirm_link_does_not_confirm_on_get(client: Client) -> None:
    # Mail scanners open links; only the POST from the page confirms.
    signup(client, "ana@unitir.edu.al")

    client.get(confirmation_url())

    assert not EmailAddress.objects.get().verified


@pytest.mark.django_db
def test_signup_cannot_grant_roles_or_staff(client: Client) -> None:
    signup(
        client,
        "ana@unitir.edu.al",
        role="ADMIN",
        professor_status="VERIFIED",
        is_staff="on",
        is_superuser="on",
    )

    user = User.objects.get()
    assert user.role == User.Role.STUDENT
    assert user.professor_status == User.ProfessorStatus.NONE
    assert not user.is_staff
    assert not user.is_superuser


@pytest.mark.django_db
def test_signup_with_existing_email_does_not_reveal_it(client: Client) -> None:
    UserFactory.create(email="ana@unitir.edu.al")

    html = signup(client, "ANA@unitir.edu.al")

    assert User.objects.count() == 1
    assert "Kontrollo emailin" in html  # same page as a new signup
    # The owner gets a "you already have an account" email instead of a second account.
    assert len(mail.outbox) == 1
    assert "ANA@unitir.edu.al".lower() in mail.outbox[0].to


@pytest.mark.django_db
def test_signup_is_rate_limited(client: Client, settings_rate: None) -> None:
    for i in range(3):
        signup(client, f"s{i}@unitir.edu.al")

    response = client.post(reverse("account_signup"), {"email": "s9@unitir.edu.al"})

    assert response.status_code == 429


@pytest.fixture
def settings_rate(settings: pytest.FixtureRequest) -> None:
    settings.ACCOUNT_RATE_LIMITS = {"signup": "3/m/ip"}  # type: ignore[attr-defined]


@pytest.mark.django_db
def test_auth_pages_are_in_albanian_by_default(client: Client) -> None:
    for name, heading in [
        ("account_signup", "Krijo llogarinë"),
        ("account_login", "Hyr në CampusQ"),
        ("account_reset_password", "Rivendos fjalëkalimin"),
    ]:
        html = client.get(reverse(name)).content.decode()
        assert heading in html, name


@pytest.mark.django_db
def test_auth_pages_switch_to_english(client: Client) -> None:
    client.cookies[settings.LANGUAGE_COOKIE_NAME] = "en"

    html = client.get(reverse("account_signup")).content.decode()

    assert "Create your account" in html


@pytest.mark.django_db
def test_verification_email_is_in_albanian(client: Client) -> None:
    signup(client, "ana@unitir.edu.al")

    assert "Konfirmo" in mail.outbox[0].subject
    assert "CampusQ" in mail.outbox[0].body


@pytest.mark.django_db
def test_home_shows_the_users_university(client: Client) -> None:
    domain = UniversityDomainFactory.create(
        domain="new.edu.al", university__name="new.edu.al", university__status="PENDING"
    )
    user = UserFactory.create(university=domain.university, display_name="Ana")
    client.force_login(user)

    html = client.get(reverse("home")).content.decode()

    assert "Përshëndetje, Ana!" in html
    assert "new.edu.al" in html
    assert "Një administrator do ta konfirmojë" in html
