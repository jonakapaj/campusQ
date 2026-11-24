from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _

from accounts.models import User
from accounts.profile_forms import ProfileForm
from core.auth import AuthedRequest, verified_required
from social.services import user_follow_context


@verified_required
def profile(request: AuthedRequest, pk: int) -> HttpResponse:
    # One query: university and faculty are joined in. Suspended users are hidden.
    person = get_object_or_404(
        User.objects.filter(is_active=True).select_related("university", "faculty"), pk=pk
    )
    context = user_follow_context(request.user, person)
    return render(request, "accounts/profile.html", context)


@verified_required
def profile_edit(request: AuthedRequest) -> HttpResponse:
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Your profile was saved."))
        return redirect("profile", pk=request.user.pk)
    return render(request, "accounts/profile_edit.html", {"form": form})
