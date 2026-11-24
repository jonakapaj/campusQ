"""The signup email-domain policy.

- A domain ending in ``.edu.al`` may sign up.
- Any other domain may sign up only if an admin has listed it in UniversityDomain.
- Matching is exact, on the full lowercased domain after the last ``@``.
"""

from django.db import IntegrityError, transaction

from universities.models import University, UniversityDomain, normalize_domain

ACADEMIC_SUFFIX = ".edu.al"


def domain_of(email: str) -> str:
    return normalize_domain(email.rpartition("@")[2])


def is_academic_domain(domain: str) -> bool:
    # endswith(".edu.al") rejects "fake-edu.al" and "edu.al.evil.com"; the length check
    # rejects a bare "edu.al" or ".edu.al", which have no institution label.
    return domain.endswith(ACADEMIC_SUFFIX) and len(domain) > len(ACADEMIC_SUFFIX)


def is_signup_allowed(email: str) -> bool:
    domain = domain_of(email)
    return is_academic_domain(domain) or UniversityDomain.objects.filter(domain=domain).exists()


def parent_domain(domain: str) -> UniversityDomain | None:
    """The closest registered parent of `domain`, as a hint for admins (never auto-linked)."""
    labels = domain.split(".")
    candidates = [".".join(labels[i:]) for i in range(1, len(labels) - 1)]
    if not candidates:
        return None
    matches = UniversityDomain.objects.filter(domain__in=candidates).select_related("university")
    return max(matches, key=lambda d: len(d.domain), default=None)


def university_for_email(email: str) -> University | None:
    """The university for a *verified* email, creating a PENDING one for a new .edu.al domain.

    Call only after the address is verified, so junk domains never reach the admin queue.
    """
    domain = domain_of(email)
    existing = UniversityDomain.objects.select_related("university").filter(domain=domain).first()
    if existing is not None:
        return existing.university
    if not is_academic_domain(domain):
        return None
    try:
        # Two students from a new domain can verify at the same moment; the unique
        # constraints make one of them lose, and the loser reads the winner's row.
        with transaction.atomic():
            university = University.objects.create(name=domain, status=University.Status.PENDING)
            UniversityDomain.objects.create(domain=domain, university=university)
    except IntegrityError:
        return UniversityDomain.objects.select_related("university").get(domain=domain).university
    return university
