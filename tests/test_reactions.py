import pytest
from django.db import IntegrityError
from django.test import Client
from django.urls import reverse

from accounts.models import User
from posts.models import Comment, Post, PostReaction
from posts.queries import feed_posts
from tests.factories import PostFactory, UniversityFactory, UserFactory
from universities.models import University


@pytest.fixture
def uni() -> University:
    return UniversityFactory.create()


@pytest.fixture
def ana(uni: University) -> User:
    return UserFactory.create(university=uni)


@pytest.fixture
def ben(uni: University) -> User:
    return UserFactory.create(university=uni)


@pytest.fixture
def post(ana: User) -> Post:
    return PostFactory.create(author=ana)


@pytest.mark.django_db
def test_like_and_unlike(client: Client, post: Post, ben: User) -> None:
    client.force_login(ben)
    url = reverse("post_react", args=[post.pk])

    client.post(url, {"like": "1"})
    client.post(url, {"like": "1"})  # idempotent
    assert PostReaction.objects.count() == 1

    client.post(url, {"like": "0"})
    assert not PostReaction.objects.exists()


@pytest.mark.django_db
def test_cannot_like_own_post(client: Client, post: Post, ana: User) -> None:
    client.force_login(ana)

    response = client.post(reverse("post_react", args=[post.pk]), {"like": "1"})

    assert response.status_code == 404
    assert not PostReaction.objects.exists()


@pytest.mark.django_db
def test_other_university_cannot_like(client: Client, post: Post) -> None:
    client.force_login(UserFactory.create(university=UniversityFactory.create()))

    assert client.post(reverse("post_react", args=[post.pk]), {"like": "1"}).status_code == 404
    assert not PostReaction.objects.exists()


@pytest.mark.django_db
def test_unverified_cannot_like(client: Client, post: Post, uni: University) -> None:
    client.force_login(UserFactory.create(university=uni, verified=False))

    client.post(reverse("post_react", args=[post.pk]), {"like": "1"})

    assert not PostReaction.objects.exists()


def test_database_allows_one_reaction_per_user(db: None) -> None:
    post = PostFactory.create()
    user = UserFactory.create()
    PostReaction.objects.create(user=user, post=post)

    with pytest.raises(IntegrityError):
        PostReaction.objects.create(user=user, post=post)


@pytest.mark.django_db
def test_htmx_like_returns_updated_button(client: Client, post: Post, ben: User) -> None:
    client.force_login(ben)

    response = client.post(
        reverse("post_react", args=[post.pk]), {"like": "1"}, headers={"HX-Request": "true"}
    )

    html = response.content.decode()
    assert 'aria-pressed="true"' in html
    assert "<span>1</span>" in html


@pytest.mark.django_db
def test_feed_annotations_count_correctly(
    post: Post, ana: User, ben: User, uni: University
) -> None:
    carl = UserFactory.create(university=uni)
    PostReaction.objects.create(user=ben, post=post)
    PostReaction.objects.create(user=carl, post=post)
    for _ in range(3):
        Comment.objects.create(post=post, author=ben, body="x")
    Comment.objects.create(post=post, author=ben, body="hidden", is_hidden=True)

    annotated = feed_posts(ben).get(pk=post.pk)

    # Two likes x four comments would be 8 with a naive double join.
    assert annotated.like_count == 2  # type: ignore[attr-defined]
    assert annotated.comment_count == 3  # type: ignore[attr-defined]
    assert annotated.liked  # type: ignore[attr-defined]
    assert not feed_posts(ana).get(pk=post.pk).liked  # type: ignore[attr-defined]
