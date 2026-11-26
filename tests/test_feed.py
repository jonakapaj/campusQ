import pytest
from django.test import Client
from django.urls import reverse

from accounts.models import User
from social.models import CourseFollow, UserFollow
from tests.factories import CourseFactory, PostFactory, UniversityFactory, UserFactory
from universities.models import University


@pytest.fixture
def uni() -> University:
    return UniversityFactory.create()


@pytest.fixture
def ana(uni: University) -> User:
    return UserFactory.create(university=uni, display_name="Ana")


def feed(client: Client, **params: str) -> str:
    return client.get(reverse("home"), params).content.decode()


@pytest.mark.django_db
def test_logged_out_visitors_get_the_landing_page(client: Client) -> None:
    html = feed(client)

    assert "Mirë se vini në CampusQ" in html
    assert "Krijo një llogari" in html


@pytest.mark.django_db
def test_university_tab_shows_only_my_university(
    client: Client, ana: User, uni: University
) -> None:
    PostFactory.create(author=UserFactory.create(university=uni), body="Brenda universitetit")
    PostFactory.create(body="Nga një universitet tjetër")
    client.force_login(ana)

    html = feed(client, tab="university")

    assert "Brenda universitetit" in html
    assert "Nga një universitet tjetër" not in html


@pytest.mark.django_db
def test_following_tab_shows_followed_people_courses_and_own_posts(
    client: Client, ana: User, uni: University
) -> None:
    friend = UserFactory.create(university=uni)
    stranger = UserFactory.create(university=uni)
    course = CourseFactory.create(university=uni)
    UserFollow.objects.create(follower=ana, followed=friend)
    CourseFollow.objects.create(user=ana, course=course)
    PostFactory.create(author=friend, body="Nga shoku")
    PostFactory.create(author=stranger, course=course, body="Në lëndën e ndjekur")
    PostFactory.create(author=stranger, body="Nga një i panjohur")
    PostFactory.create(author=ana, body="Postimi im")
    client.force_login(ana)

    html = feed(client)  # defaults to "following" once you follow something

    assert "Nga shoku" in html
    assert "Në lëndën e ndjekur" in html
    assert "Postimi im" in html
    assert "Nga një i panjohur" not in html


@pytest.mark.django_db
def test_following_someone_elsewhere_does_not_leak_their_posts(client: Client, ana: User) -> None:
    elsewhere = UserFactory.create(university=UniversityFactory.create())
    UserFollow.objects.create(follower=ana, followed=elsewhere)
    PostFactory.create(author=elsewhere, body="Privat për universitetin tim")
    client.force_login(ana)

    html = feed(client, tab="following")

    assert "Privat për universitetin tim" not in html


@pytest.mark.django_db
def test_without_follows_the_feed_defaults_to_university(
    client: Client, ana: User, uni: University
) -> None:
    PostFactory.create(author=UserFactory.create(university=uni), body="Lajm")
    client.force_login(ana)

    html = feed(client)

    assert "Lajm" in html
    assert 'href="?tab=university" class="rounded-md px-3 py-1.5 font-medium bg-white' in html


@pytest.mark.django_db
def test_feed_paginates(client: Client, ana: User, uni: University) -> None:
    author = UserFactory.create(university=uni)
    for i in range(25):
        PostFactory.create(author=author, body=f"postimi-{i:02d}")
    client.force_login(ana)

    first = feed(client, tab="university")
    second = feed(client, tab="university", page="2")

    assert "postimi-24" in first
    assert "postimi-04" not in first
    assert "postimi-04" in second
    assert "postimi-24" not in second


@pytest.mark.django_db
def test_unknown_tab_falls_back_to_university(client: Client, ana: User) -> None:
    client.force_login(ana)

    assert client.get(reverse("home"), {"tab": "<script>"}).status_code == 200


@pytest.mark.django_db
def test_feed_query_count_is_flat(
    client: Client, ana: User, uni: University, django_assert_max_num_queries: object
) -> None:
    from core.images import process_image
    from posts.models import Comment, PostImage, PostReaction
    from tests.images import png

    def add_posts(n: int) -> None:
        for _ in range(n):
            author = UserFactory.create(university=uni)
            post = PostFactory.create(author=author, course=CourseFactory.create(university=uni))
            PostReaction.objects.create(user=ana, post=post)
            Comment.objects.create(post=post, author=author, body="c")
            PostImage.objects.create(post=post, image=process_image(png()))

    client.force_login(ana)
    add_posts(2)
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    with CaptureQueriesContext(connection) as small:
        feed(client, tab="university")
    add_posts(15)
    with CaptureQueriesContext(connection) as large:
        feed(client, tab="university")

    assert len(large) == len(small)
