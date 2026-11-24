import pytest
from django.db import IntegrityError
from django.test import Client
from django.urls import reverse

from accounts.models import User
from social.models import CourseFollow, UserFollow
from tests.factories import CourseFactory, UniversityFactory, UserFactory
from universities.models import University

HTMX = {"HX-Request": "true"}


@pytest.fixture
def ana() -> User:
    return UserFactory.create(display_name="Ana")


@pytest.fixture
def ben() -> User:
    return UserFactory.create(display_name="Ben")


@pytest.mark.django_db
def test_follow_and_unfollow_a_user(client: Client, ana: User, ben: User) -> None:
    client.force_login(ana)
    url = reverse("follow_user", args=[ben.pk])

    response = client.post(url, {"follow": "1"})
    assert response.status_code == 302
    assert UserFollow.objects.filter(follower=ana, followed=ben).exists()

    client.post(url, {"follow": "0"})
    assert not UserFollow.objects.exists()


@pytest.mark.django_db
def test_following_twice_is_idempotent(client: Client, ana: User, ben: User) -> None:
    client.force_login(ana)
    url = reverse("follow_user", args=[ben.pk])

    client.post(url, {"follow": "1"})
    client.post(url, {"follow": "1"})

    assert UserFollow.objects.count() == 1


@pytest.mark.django_db
def test_cannot_follow_yourself(client: Client, ana: User) -> None:
    client.force_login(ana)

    response = client.post(reverse("follow_user", args=[ana.pk]), {"follow": "1"})

    assert response.status_code == 404
    assert not UserFollow.objects.exists()


def test_database_also_rejects_self_follow(db: None) -> None:
    ana = UserFactory.create()
    with pytest.raises(IntegrityError):
        UserFollow.objects.create(follower=ana, followed=ana)


@pytest.mark.django_db
def test_cannot_follow_a_suspended_user(client: Client, ana: User, ben: User) -> None:
    ben.is_active = False
    ben.save()
    client.force_login(ana)

    response = client.post(reverse("follow_user", args=[ben.pk]), {"follow": "1"})

    assert response.status_code == 404


@pytest.mark.django_db
def test_follow_requires_login_and_post(client: Client, ana: User, ben: User) -> None:
    url = reverse("follow_user", args=[ben.pk])

    assert client.post(url, {"follow": "1"}).status_code == 302  # to login
    client.force_login(ana)
    assert client.get(url).status_code == 405
    assert not UserFollow.objects.exists()


@pytest.mark.django_db
def test_htmx_follow_returns_just_the_button(client: Client, ana: User, ben: User) -> None:
    client.force_login(ana)

    response = client.post(reverse("follow_user", args=[ben.pk]), {"follow": "1"}, headers=HTMX)

    html = response.content.decode()
    assert response.status_code == 200
    assert "<html" not in html
    assert "Po ndjek" in html  # "Following"
    assert "<strong>1</strong> ndjekës" in html


@pytest.mark.django_db
def test_profile_shows_counts_and_follow_state(client: Client, ana: User, ben: User) -> None:
    UserFollow.objects.create(follower=ana, followed=ben)
    client.force_login(ana)

    html = client.get(reverse("profile", args=[ben.pk])).content.decode()

    assert "<strong>1</strong> ndjekës" in html
    assert 'name="follow" value="0"' in html  # unfollow form


@pytest.mark.django_db
def test_own_profile_has_no_follow_button(client: Client, ana: User) -> None:
    client.force_login(ana)

    html = client.get(reverse("profile", args=[ana.pk])).content.decode()

    assert reverse("follow_user", args=[ana.pk]) not in html


@pytest.mark.django_db
def test_follow_and_unfollow_a_course(client: Client, ana: User) -> None:
    course = CourseFactory.create()
    client.force_login(ana)
    url = reverse("follow_course", args=[course.pk])

    client.post(url, {"follow": "1"})
    assert CourseFollow.objects.filter(user=ana, course=course).exists()
    client.post(url, {"follow": "0"})
    assert not CourseFollow.objects.exists()


@pytest.mark.django_db
def test_cannot_follow_a_course_of_someone_elses_pending_university(
    client: Client, ana: User
) -> None:
    course = CourseFactory.create(
        university=UniversityFactory.create(status=University.Status.PENDING)
    )
    client.force_login(ana)

    response = client.post(reverse("follow_course", args=[course.pk]), {"follow": "1"})

    assert response.status_code == 404
    assert not CourseFollow.objects.exists()


@pytest.mark.django_db
def test_followers_and_following_lists(client: Client, ana: User, ben: User) -> None:
    course = CourseFactory.create(name="Algjebër Lineare")
    UserFollow.objects.create(follower=ana, followed=ben)
    CourseFollow.objects.create(user=ana, course=course)
    client.force_login(ben)

    followers = client.get(reverse("followers", args=[ben.pk])).content.decode()
    following = client.get(reverse("following", args=[ana.pk])).content.decode()

    assert "Ana" in followers
    assert "Ben" in following
    assert "Algjebër Lineare" in following


@pytest.mark.django_db
def test_following_list_hides_suspended_users(client: Client, ana: User, ben: User) -> None:
    UserFollow.objects.create(follower=ana, followed=ben)
    ben.is_active = False
    ben.save()
    client.force_login(ana)

    html = client.get(reverse("following", args=[ana.pk])).content.decode()

    assert "Ben" not in html


@pytest.mark.django_db
def test_deleting_a_user_removes_their_follows(ana: User, ben: User) -> None:
    UserFollow.objects.create(follower=ana, followed=ben)
    CourseFollow.objects.create(user=ana, course=CourseFactory.create())

    ana.delete()

    assert not UserFollow.objects.exists()
    assert not CourseFollow.objects.exists()
