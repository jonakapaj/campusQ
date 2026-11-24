from typing import Any

import factory
from allauth.account.models import EmailAddress

from accounts.models import User
from universities.models import University, UniversityDomain


class UniversityFactory(factory.django.DjangoModelFactory[University]):
    class Meta:
        model = University

    name = factory.Sequence(lambda n: f"Universiteti {n}")
    short_name = factory.Sequence(lambda n: f"U{n}")
    city = "Tiranë"
    status = University.Status.ACTIVE


class UniversityDomainFactory(factory.django.DjangoModelFactory[UniversityDomain]):
    class Meta:
        model = UniversityDomain

    domain = factory.Sequence(lambda n: f"uni{n}.edu.al")
    university = factory.SubFactory(UniversityFactory)


class UserFactory(factory.django.DjangoModelFactory[User]):
    class Meta:
        model = User
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f"student{n}@unitir.edu.al")
    display_name = "Ana Hoxha"
    password = factory.django.Password("correct-horse-battery")

    @factory.post_generation
    def verified(obj: User, create: bool, extracted: bool | None, **kwargs: Any) -> None:  # noqa: N805
        if create and extracted is not False:
            EmailAddress.objects.create(user=obj, email=obj.email, primary=True, verified=True)
