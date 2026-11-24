import pytest
from django.db import IntegrityError

from accounts.models import User
from tests.factories import UserFactory


@pytest.mark.django_db
def test_email_is_stored_lowercase() -> None:
    user = User.objects.create_user("Ana.Hoxha@UNITIR.edu.al", "pw", display_name="Ana")

    assert user.email == "ana.hoxha@unitir.edu.al"


@pytest.mark.django_db
def test_emails_are_unique_regardless_of_case() -> None:
    User.objects.create_user("ana@unitir.edu.al", "pw", display_name="Ana")

    with pytest.raises(IntegrityError):
        User.objects.create_user("ANA@unitir.edu.al", "pw", display_name="Ana")


@pytest.mark.django_db
def test_new_users_are_plain_students() -> None:
    user = UserFactory.create()

    assert user.role == User.Role.STUDENT
    assert user.professor_status == User.ProfessorStatus.NONE
    assert not user.is_staff
    assert not user.is_superuser
    assert not user.is_verified_professor


@pytest.mark.django_db
def test_superuser_is_an_admin() -> None:
    admin = User.objects.create_superuser("root@unitir.edu.al", "pw", display_name="Root")

    assert admin.is_staff
    assert admin.is_superuser
    assert admin.role == User.Role.ADMIN


@pytest.mark.django_db
def test_database_rejects_a_verified_student() -> None:
    user = UserFactory.create()
    user.professor_status = User.ProfessorStatus.VERIFIED

    with pytest.raises(IntegrityError):
        user.save()


@pytest.mark.django_db
def test_verified_professor() -> None:
    user = UserFactory.create(
        role=User.Role.PROFESSOR, professor_status=User.ProfessorStatus.VERIFIED
    )

    assert user.is_verified_professor


@pytest.mark.django_db
def test_natural_key_lookup_ignores_case() -> None:
    user = UserFactory.create(email="ana@unitir.edu.al")

    assert User.objects.get_by_natural_key("ANA@UniTir.edu.al") == user
