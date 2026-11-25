"""Access guards shared by every app."""

from collections.abc import Callable
from typing import TYPE_CHECKING, Concatenate, cast

from allauth.account.decorators import verified_email_required
from django.http import HttpRequest
from django.http.response import HttpResponseBase

if TYPE_CHECKING:
    from accounts.models import User


class AuthedRequest(HttpRequest):
    """A request that passed `verified_required`, so `.user` is a real, verified User."""

    user: "User"


def verified_required[**P](
    view: Callable[Concatenate[AuthedRequest, P], HttpResponseBase],
) -> Callable[Concatenate[HttpRequest, P], HttpResponseBase]:
    """Logged in *and* email verified. Every page with user content uses this.

    Signup already blocks unverified sign-in; this also covers accounts that got a
    session another way (e.g. the Django admin login).
    """
    return cast(
        "Callable[Concatenate[HttpRequest, P], HttpResponseBase]", verified_email_required(view)
    )
