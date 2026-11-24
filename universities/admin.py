from django.contrib import admin, messages
from django.db.models import Count, QuerySet
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext

from universities.domains import parent_domain
from universities.models import University, UniversityDomain


class UniversityDomainInline(admin.TabularInline[UniversityDomain, University]):
    model = UniversityDomain
    extra = 0


@admin.register(University)
class UniversityAdmin(admin.ModelAdmin[University]):
    list_display = ("name", "short_name", "city", "status", "domain_list", "member_count")
    list_filter = ("status",)
    search_fields = ("name", "short_name", "domains__domain")
    readonly_fields = ("parent_hint", "created_at")
    inlines = (UniversityDomainInline,)
    actions = ("activate",)

    def get_queryset(self, request: HttpRequest) -> QuerySet[University]:
        # One query for the domains of every row, and the member count as an annotation,
        # instead of two extra queries per row.
        return (
            super()
            .get_queryset(request)
            .prefetch_related("domains")
            .annotate(member_count=Count("members", distinct=True))
        )

    @admin.display(description=_("domains"))
    def domain_list(self, obj: University) -> str:
        return ", ".join(d.domain for d in obj.domains.all())

    @admin.display(description=_("members"), ordering="member_count")
    def member_count(self, obj: University) -> int:
        return obj.member_count  # type: ignore[attr-defined, no-any-return]

    @admin.display(description=_("possible parent university"))
    def parent_hint(self, obj: University) -> str:
        for d in obj.domains.all():
            parent = parent_domain(d.domain)
            if parent is not None:
                return f"{parent.university} ({parent.domain})"
        return "-"

    @admin.action(description=_("Mark selected universities as active"))
    def activate(self, request: HttpRequest, queryset: QuerySet[University]) -> None:
        count = queryset.update(status=University.Status.ACTIVE)
        self.message_user(
            request,
            ngettext("%d university activated.", "%d universities activated.", count) % count,
            messages.SUCCESS,
        )


@admin.register(UniversityDomain)
class UniversityDomainAdmin(admin.ModelAdmin[UniversityDomain]):
    list_display = ("domain", "university")
    list_select_related = ("university",)
    search_fields = ("domain", "university__name")
    autocomplete_fields = ("university",)
