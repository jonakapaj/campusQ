import pytest
from django.core.exceptions import ValidationError

from tests.factories import UniversityDomainFactory, UniversityFactory
from universities.domains import (
    domain_of,
    is_academic_domain,
    is_signup_allowed,
    parent_domain,
    university_for_email,
)
from universities.models import University, UniversityDomain


@pytest.mark.parametrize(
    ("email", "domain"),
    [
        ("ana@unitir.edu.al", "unitir.edu.al"),
        ("Ana@UniTir.EDU.AL", "unitir.edu.al"),
        ('"a@b"@unitir.edu.al', "unitir.edu.al"),  # the domain is after the *last* @
        ("ana@unitir.edu.al ", "unitir.edu.al"),
    ],
)
def test_domain_of(email: str, domain: str) -> None:
    assert domain_of(email) == domain


@pytest.mark.parametrize(
    "domain",
    ["unitir.edu.al", "students.unitir.edu.al", "upt.edu.al", "uamd.edu.al"],
)
def test_academic_domains(domain: str) -> None:
    assert is_academic_domain(domain)


@pytest.mark.parametrize(
    "domain",
    [
        "fake-edu.al",  # suffix without the dot
        "edu.al.evil.com",  # .edu.al in the middle
        "edu.al",  # no institution label
        ".edu.al",
        "unitir.edu.al.",
        "gmail.com",
        "upt.al",  # needs an allowlist row
        "unitir.edu.al.al",
        "unitir.edu.alx",
    ],
)
def test_non_academic_domains(domain: str) -> None:
    assert not is_academic_domain(domain)


@pytest.mark.django_db
def test_any_edu_al_email_may_sign_up() -> None:
    assert is_signup_allowed("ana@unknown.edu.al")


@pytest.mark.django_db
@pytest.mark.parametrize(
    "email", ["x@fake-edu.al", "x@edu.al.evil.com", "x@edu.al", "x@gmail.com", "x@upt.al"]
)
def test_non_academic_email_is_rejected(email: str) -> None:
    assert not is_signup_allowed(email)


@pytest.mark.django_db
def test_allowlisted_domain_outside_edu_al_may_sign_up() -> None:
    UniversityDomainFactory.create(domain="upt.al")

    assert is_signup_allowed("staff@UPT.al")
    assert not is_signup_allowed("staff@sub.upt.al")  # exact match only


@pytest.mark.django_db
def test_known_domain_resolves_to_its_university() -> None:
    domain = UniversityDomainFactory.create(domain="unitir.edu.al")

    assert university_for_email("ana@UNITIR.edu.al") == domain.university
    assert University.objects.count() == 1


@pytest.mark.django_db
def test_unknown_edu_al_domain_creates_one_pending_university() -> None:
    first = university_for_email("a@new.edu.al")
    second = university_for_email("b@new.edu.al")

    assert first is not None
    assert first == second
    assert first.status == University.Status.PENDING
    assert list(first.domains.values_list("domain", flat=True)) == ["new.edu.al"]


@pytest.mark.django_db
def test_unknown_subdomain_is_not_linked_to_the_parent_university() -> None:
    parent = UniversityDomainFactory.create(domain="unitir.edu.al")

    university = university_for_email("a@students.unitir.edu.al")

    assert university is not None
    assert university != parent.university
    assert university.status == University.Status.PENDING
    assert parent_domain("students.unitir.edu.al") == parent


@pytest.mark.django_db
def test_parent_domain_prefers_the_closest_parent() -> None:
    UniversityDomainFactory.create(domain="unitir.edu.al")
    closest = UniversityDomainFactory.create(domain="fshn.unitir.edu.al")

    assert parent_domain("students.fshn.unitir.edu.al") == closest
    assert parent_domain("unitir.edu.al") is None


@pytest.mark.django_db
def test_non_academic_unlisted_domain_gets_no_university() -> None:
    assert university_for_email("a@gmail.com") is None
    assert not University.objects.exists()


@pytest.mark.django_db
def test_domains_are_stored_lowercase_and_unique() -> None:
    university = UniversityFactory.create()
    UniversityDomain.objects.create(domain=" UniTir.EDU.al ", university=university)

    assert UniversityDomain.objects.get().domain == "unitir.edu.al"
    with pytest.raises(ValidationError) as excinfo:
        UniversityDomain(domain="UNITIR.edu.al", university=university).full_clean()
    assert excinfo.value.error_dict["domain"][0].code == "unique"
