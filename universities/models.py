import re
from typing import Any

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

# A DNS hostname with at least two labels: letters, digits and inner hyphens.
_DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)(?!-)[a-z0-9-]{1,63}(?<!-)(\.(?!-)[a-z0-9-]{1,63}(?<!-))+$",
    re.IGNORECASE,
)


def normalize_domain(domain: str) -> str:
    return domain.strip().lower()


def validate_domain(value: str) -> None:
    if not _DOMAIN_RE.match(normalize_domain(value)):
        raise ValidationError(
            _("Enter a domain such as unitir.edu.al, without @ or http://."),
            code="invalid_domain",
        )


class University(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", _("Active")
        PENDING = "PENDING", _("Pending review")

    name = models.CharField(_("name"), max_length=200, unique=True)
    short_name = models.CharField(
        _("short name"), max_length=20, blank=True, help_text=_("For example UT, UPT or UAMD.")
    )
    city = models.CharField(_("city"), max_length=100, blank=True)
    status = models.CharField(
        _("status"), max_length=10, choices=Status.choices, default=Status.PENDING
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)

    class Meta:
        ordering = ("name",)
        verbose_name = _("university")
        verbose_name_plural = _("universities")

    def __str__(self) -> str:
        return self.name

    @property
    def is_active(self) -> bool:
        return self.status == self.Status.ACTIVE


class UniversityDomain(models.Model):
    """An email domain that may sign up, and the university it belongs to.

    This table is also the allowlist: a domain outside .edu.al can sign up only if an
    admin has added it here. Domains match exactly, never by parent domain.
    """

    domain = models.CharField(
        _("domain"), max_length=253, unique=True, validators=[validate_domain]
    )
    university = models.ForeignKey(
        University,
        on_delete=models.CASCADE,
        related_name="domains",
        verbose_name=_("university"),
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)

    class Meta:
        ordering = ("domain",)
        verbose_name = _("email domain")
        verbose_name_plural = _("email domains")

    def __str__(self) -> str:
        return self.domain

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.domain = normalize_domain(self.domain)
        super().save(*args, **kwargs)

    def clean(self) -> None:
        # Normalise before the unique check so "UniTir.edu.al" collides with "unitir.edu.al".
        self.domain = normalize_domain(self.domain)
