from typing import Any

from allauth.account.models import EmailAddress
from allauth.account.signals import email_confirmed
from django.dispatch import receiver
from django.http import HttpRequest

from universities.domains import university_for_email


@receiver(email_confirmed)
def link_university(
    sender: object, request: HttpRequest, email_address: EmailAddress, **kwargs: Any
) -> None:
    """Link the user to their university once they have proven they own the address.

    Doing this only after verification means an unknown .edu.al domain becomes a
    PENDING university for admins to review only when a real person controls it.
    """
    user = email_address.user
    university = university_for_email(email_address.email)
    if university is not None and user.university_id != university.pk:
        user.university = university
        user.save(update_fields=["university"])
