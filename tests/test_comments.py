import pytest
from django.test import Client
from django.urls import reverse

from accounts.models import User
from posts.models import Comment, Post
from tests.factories import PostFactory, UniversityFactory, UserFactory
from universities.models import University


@pytest.fixture
def uni() -> University:
    return UniversityFactory.create()


@pytest.fixture
def ana(uni: University) -> User:
    return UserFactory.create(university=uni, display_name="Ana")


@pytest.fixture
def post(ana: User) -> Post:
    return PostFactory.create(author=ana)


@pytest.mark.django_db
def test_classmate_can_comment(client: Client, post: Post, uni: University) -> None:
    ben = UserFactory.create(university=uni, display_name="Ben")
    client.force_login(ben)

    response = client.post(reverse("comment_create", args=[post.pk]), {"body": "Faleminderit!"})

    comment = Comment.objects.get()
    assert response.status_code == 302
    assert comment.author == ben
    assert comment.post == post
    html = client.get(reverse("post_detail", args=[post.pk])).content.decode()
    assert "Faleminderit!" in html


@pytest.mark.django_db
def test_htmx_comment_returns_form_and_appended_comment(
    client: Client, post: Post, ana: User
) -> None:
    client.force_login(ana)

    response = client.post(
        reverse("comment_create", args=[post.pk]), {"body": "Po"}, headers={"HX-Request": "true"}
    )

    html = response.content.decode()
    assert 'hx-swap-oob="beforeend:#comments"' in html
    assert "Po" in html
    assert "<html" not in html


@pytest.mark.django_db
def test_other_university_cannot_comment(client: Client, post: Post) -> None:
    client.force_login(UserFactory.create(university=UniversityFactory.create()))

    response = client.post(reverse("comment_create", args=[post.pk]), {"body": "hi"})

    assert response.status_code == 404
    assert not Comment.objects.exists()


@pytest.mark.django_db
def test_cannot_comment_on_hidden_post(client: Client, post: Post, uni: University) -> None:
    Post.objects.filter(pk=post.pk).update(is_hidden=True)
    client.force_login(UserFactory.create(university=uni))

    assert client.post(reverse("comment_create", args=[post.pk]), {"body": "x"}).status_code == 404


@pytest.mark.django_db
def test_questions_do_not_take_comments(client: Client, ana: User) -> None:
    question = PostFactory.create(author=ana, kind=Post.Kind.QUESTION, title="Pyetje?")
    client.force_login(ana)

    assert (
        client.post(reverse("comment_create", args=[question.pk]), {"body": "x"}).status_code == 404
    )


@pytest.mark.django_db
def test_empty_comment_is_rejected(client: Client, post: Post, ana: User) -> None:
    client.force_login(ana)

    client.post(reverse("comment_create", args=[post.pk]), {"body": "  "})

    assert not Comment.objects.exists()


@pytest.mark.django_db
def test_comment_too_long_is_rejected(client: Client, post: Post, ana: User) -> None:
    client.force_login(ana)

    client.post(reverse("comment_create", args=[post.pk]), {"body": "x" * 2001})

    assert not Comment.objects.exists()


@pytest.mark.django_db
def test_comment_html_is_escaped(client: Client, post: Post, ana: User) -> None:
    Comment.objects.create(post=post, author=ana, body="<img src=x onerror=alert(1)>")
    client.force_login(ana)

    html = client.get(reverse("post_detail", args=[post.pk])).content.decode()

    assert "<img src=x onerror" not in html


@pytest.mark.django_db
def test_hidden_comments_and_suspended_authors_are_not_shown(
    client: Client, post: Post, uni: University
) -> None:
    Comment.objects.create(
        post=post, author=UserFactory.create(university=uni), body="fshehur", is_hidden=True
    )
    Comment.objects.create(
        post=post, author=UserFactory.create(university=uni, is_active=False), body="pezulluar"
    )
    client.force_login(UserFactory.create(university=uni))

    html = client.get(reverse("post_detail", args=[post.pk])).content.decode()

    assert "fshehur" not in html
    assert "pezulluar" not in html


@pytest.mark.django_db
def test_only_author_or_admin_can_delete_a_comment(
    client: Client, post: Post, ana: User, uni: University
) -> None:
    ben = UserFactory.create(university=uni)
    c1 = Comment.objects.create(post=post, author=ben, body="1")
    c2 = Comment.objects.create(post=post, author=ben, body="2")

    client.force_login(ana)  # the post author, but not the comment author
    assert client.post(reverse("comment_delete", args=[c1.pk])).status_code == 404
    client.force_login(ben)
    client.post(reverse("comment_delete", args=[c1.pk]))
    client.force_login(UserFactory.create(role=User.Role.ADMIN))
    client.post(reverse("comment_delete", args=[c2.pk]))

    assert not Comment.objects.exists()


@pytest.mark.django_db
def test_comment_list_has_no_n_plus_one(
    client: Client, post: Post, ana: User, uni: University, django_assert_max_num_queries: object
) -> None:
    for i in range(10):
        Comment.objects.create(post=post, author=UserFactory.create(university=uni), body=str(i))
    client.force_login(ana)
    client.get(reverse("post_detail", args=[post.pk]))

    with django_assert_max_num_queries(12):  # type: ignore[operator]
        client.get(reverse("post_detail", args=[post.pk]))
