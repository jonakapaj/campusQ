from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import BaseUserCreationForm
from django.contrib.auth.forms import UserChangeForm as DjangoUserChangeForm
from django.utils.translation import gettext_lazy as _

from accounts.models import User


class UserCreationForm(BaseUserCreationForm[User]):
    class Meta:
        model = User
        fields = ("email", "display_name")


class UserChangeForm(DjangoUserChangeForm[User]):
    class Meta:
        model = User
        fields = "__all__"


@admin.register(User)
# django-stubs bounds UserAdmin to AbstractUser; ours is AbstractBaseUser + PermissionsMixin.
class UserAdmin(DjangoUserAdmin[User]):  # type: ignore[type-var]
    form = UserChangeForm
    add_form = UserCreationForm
    ordering = ("email",)
    list_display = ("email", "display_name", "university", "role", "professor_status", "is_staff")
    list_filter = ("role", "professor_status", "is_staff", "is_active", "university__status")
    list_select_related = ("university",)  # avoids one query per row for the column
    search_fields = ("email", "display_name")
    autocomplete_fields = ("university", "faculty")
    readonly_fields = ("last_login", "date_joined")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            _("Profile"),
            {"fields": ("display_name", "university", "faculty", "field_of_study", "year", "bio")},
        ),
        (_("Role"), {"fields": ("role", "professor_status")}),
        (
            _("Permissions"),
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "display_name", "password1", "password2"),
            },
        ),
    )
