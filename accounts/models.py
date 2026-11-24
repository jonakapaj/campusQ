from typing import Any, ClassVar

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from universities.models import Faculty, University

# Medicine has 6 years; bachelor 3, master 2.
MAX_STUDY_YEAR = 6


class UserManager(BaseUserManager["User"]):
    use_in_migrations = True

    @classmethod
    def normalize_email(cls, email: str | None) -> str:
        # Django only lowercases the domain. Lowercase it all so "Ana@UNITIR.edu.al" and
        # "ana@unitir.edu.al" can't become two accounts.
        return (email or "").strip().lower()

    def get_by_natural_key(self, username: str | None) -> "User":
        return self.get(email=self.normalize_email(username))

    def create_user(self, email: str, password: str | None = None, **extra: Any) -> "User":
        if not email:
            raise ValueError("Users must have an email address")
        user = self.model(email=self.normalize_email(email), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str | None = None, **extra: Any) -> "User":
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("role", User.Role.ADMIN)
        return self.create_user(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        STUDENT = "STUDENT", _("Student")
        PROFESSOR = "PROFESSOR", _("Professor")
        ADMIN = "ADMIN", _("Admin")

    class ProfessorStatus(models.TextChoices):
        NONE = "NONE", _("None")
        PENDING = "PENDING", _("Pending")
        VERIFIED = "VERIFIED", _("Verified")
        REJECTED = "REJECTED", _("Rejected")

    email = models.EmailField(_("email address"), unique=True)
    display_name = models.CharField(_("display name"), max_length=60)
    role = models.CharField(_("role"), max_length=10, choices=Role.choices, default=Role.STUDENT)
    professor_status = models.CharField(
        _("professor status"),
        max_length=10,
        choices=ProfessorStatus.choices,
        default=ProfessorStatus.NONE,
    )
    university = models.ForeignKey(
        University,
        on_delete=models.PROTECT,  # deleting a university must never delete its members
        null=True,
        blank=True,
        related_name="members",
        verbose_name=_("university"),
    )
    # Profile. Faculty must belong to the user's university (enforced in ProfileForm).
    faculty = models.ForeignKey(
        Faculty,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="members",
        verbose_name=_("faculty"),
    )
    field_of_study = models.CharField(_("field of study"), max_length=100, blank=True)
    year = models.PositiveSmallIntegerField(
        _("year of study"),
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(MAX_STUDY_YEAR)],
    )
    bio = models.TextField(_("bio"), max_length=500, blank=True)

    is_active = models.BooleanField(_("active"), default=True)
    is_staff = models.BooleanField(
        _("staff status"),
        default=False,
        help_text=_("Can log in to this admin site."),
    )
    date_joined = models.DateTimeField(_("date joined"), default=timezone.now)

    objects: ClassVar[UserManager] = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS: ClassVar[list[str]] = ["display_name"]

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        constraints: ClassVar = [
            # Only professors can be verified professors, whatever code path sets the fields.
            models.CheckConstraint(
                condition=~Q(professor_status="VERIFIED") | Q(role="PROFESSOR"),
                name="verified_professor_has_professor_role",
            ),
            models.CheckConstraint(
                condition=Q(year__isnull=True) | Q(year__gte=1, year__lte=MAX_STUDY_YEAR),
                name="user_year_in_range",
            ),
        ]

    def __str__(self) -> str:
        return self.email

    def clean(self) -> None:
        super().clean()
        self.email = UserManager.normalize_email(self.email)

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.email = UserManager.normalize_email(self.email)
        super().save(*args, **kwargs)

    def get_full_name(self) -> str:
        return self.display_name or self.email

    def get_short_name(self) -> str:
        return self.get_full_name()

    @property
    def initials(self) -> str:
        """Up to two letters for the avatar circle, e.g. "Ëngjëll Çela" -> "ËÇ"."""
        words = self.get_full_name().split()
        return "".join(w[0] for w in words[:2]).upper() or "?"

    @property
    def is_platform_admin(self) -> bool:
        """Runs moderation and professor review. Never derived from client input."""
        return self.is_active and (self.is_superuser or self.role == self.Role.ADMIN)

    @property
    def is_verified_professor(self) -> bool:
        return (
            self.role == self.Role.PROFESSOR
            and self.professor_status == self.ProfessorStatus.VERIFIED
        )


def user_display(user: User) -> str:
    """How allauth names a user in messages (ACCOUNT_USER_DISPLAY)."""
    return user.get_full_name()
