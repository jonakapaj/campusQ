import pytest
from django.db import IntegrityError
from django.test import Client
from django.urls import reverse

from accounts.models import User
from posts.models import Post
from tests.factories import CourseFactory, PostFactory, UniversityFactory, UserFactory
from universities.models import University


@pytest.fixture
def uni() -> University:
    return UniversityFactory.create()


@pytest.fixture
def ana(uni: University) -> User:
    return UserFactory.create(university=uni, display_name="Ana")


@pytest.fixture
def outsider() -> User:
    return UserFactory.create(university=UniversityFactory.create(), display_name="Outsider")


@pytest.mark.django_db
def test_create_post_sets_author_and_university_server_side(
    client: Client, ana: User, uni: University
) -> None:
    other_uni = UniversityFactory.create()
    client.force_login(ana)

    response = client.post(
        reverse("post_create"),
        {
            "body": "Kush ka **shënimet** e javës?",
            "author": UserFactory.create().pk,
            "university": other_uni.pk,
            "kind": "QUESTION",
            "is_anonymous": "on",
            "is_hidden": "on",
        },
    )

    post = Post.objects.get()
    assert response.status_code == 302
    assert post.author == ana
    assert post.university == uni
    assert post.kind == Post.Kind.POST
    assert not post.is_anonymous
    assert not post.is_hidden
    assert "<strong>shënimet</strong>" in post.body_html


@pytest.mark.django_db
def test_post_in_a_course_of_your_university(client: Client, ana: User, uni: University) -> None:
    course = CourseFactory.create(university=uni)
    client.force_login(ana)

    client.post(reverse("post_create"), {"body": "Pyetje", "course": course.pk})

    assert Post.objects.get().course == course


@pytest.mark.django_db
def test_cannot_post_in_a_course_of_another_university(client: Client, ana: User) -> None:
    foreign = CourseFactory.create()
    client.force_login(ana)

    response = client.post(reverse("post_create"), {"body": "Hi", "course": foreign.pk})

    assert response.status_code == 200
    assert not Post.objects.exists()


@pytest.mark.django_db
def test_empty_post_is_rejected(client: Client, ana: User) -> None:
    client.force_login(ana)

    client.post(reverse("post_create"), {"body": "   "})

    assert not Post.objects.exists()


@pytest.mark.django_db
def test_user_without_university_cannot_post(client: Client) -> None:
    client.force_login(UserFactory.create(university=None))

    response = client.post(reverse("post_create"), {"body": "Hi"})

    assert response.status_code == 302
    assert not Post.objects.exists()


@pytest.mark.django_db
def test_posting_requires_verified_email(client: Client, uni: University) -> None:
    client.force_login(UserFactory.create(university=uni, verified=False))

    client.post(reverse("post_create"), {"body": "Hi"})

    assert not Post.objects.exists()


@pytest.mark.django_db
def test_members_see_their_universitys_posts(client: Client, ana: User, uni: University) -> None:
    post = PostFactory.create(author=UserFactory.create(university=uni), body="Takim në 5")
    client.force_login(ana)

    response = client.get(reverse("post_detail", args=[post.pk]))

    assert response.status_code == 200
    assert "Takim në 5" in response.content.decode()


@pytest.mark.django_db
def test_other_universities_cannot_see_a_post(client: Client, ana: User, outsider: User) -> None:
    post = PostFactory.create(author=ana)
    client.force_login(outsider)

    assert client.get(reverse("post_detail", args=[post.pk])).status_code == 404


@pytest.mark.django_db
def test_other_universities_cannot_see_course_posts(
    client: Client, ana: User, uni: University, outsider: User
) -> None:
    course = CourseFactory.create(university=uni)
    PostFactory.create(author=ana, course=course, body="Sekret i kursit")
    client.force_login(outsider)

    html = client.get(reverse("course_detail", args=[course.pk])).content.decode()

    assert "Sekret i kursit" not in html


@pytest.mark.django_db
def test_hidden_posts_and_suspended_authors_are_not_visible(
    client: Client, ana: User, uni: University
) -> None:
    hidden = PostFactory.create(author=ana, is_hidden=True)
    suspended = UserFactory.create(university=uni, is_active=False)
    by_suspended = PostFactory.create(author=suspended)
    client.force_login(UserFactory.create(university=uni))

    assert client.get(reverse("post_detail", args=[hidden.pk])).status_code == 404
    assert client.get(reverse("post_detail", args=[by_suspended.pk])).status_code == 404


@pytest.mark.django_db
def test_admins_can_see_everything(client: Client, ana: User) -> None:
    post = PostFactory.create(author=ana, is_hidden=True)
    client.force_login(UserFactory.create(role=User.Role.ADMIN, university=None))

    assert client.get(reverse("post_detail", args=[post.pk])).status_code == 200


@pytest.mark.django_db
def test_author_can_edit_and_others_cannot(client: Client, ana: User, uni: University) -> None:
    post = PostFactory.create(author=ana, body="old")
    classmate = UserFactory.create(university=uni)

    client.force_login(classmate)
    assert client.post(reverse("post_edit", args=[post.pk]), {"body": "hacked"}).status_code == 404
    client.force_login(ana)
    client.post(reverse("post_edit", args=[post.pk]), {"body": "new *text*"})

    post.refresh_from_db()
    assert post.body == "new *text*"
    assert "<em>text</em>" in post.body_html


@pytest.mark.django_db
def test_edit_cannot_move_a_post_to_another_university(
    client: Client, ana: User, uni: University
) -> None:
    post = PostFactory.create(author=ana)
    client.force_login(ana)

    client.post(
        reverse("post_edit", args=[post.pk]),
        {"body": "x", "university": UniversityFactory.create().pk},
    )

    post.refresh_from_db()
    assert post.university == uni


@pytest.mark.django_db
def test_author_and_admin_can_delete_but_classmates_cannot(
    client: Client, ana: User, uni: University
) -> None:
    mine = PostFactory.create(author=ana)
    other = PostFactory.create(author=ana)

    client.force_login(UserFactory.create(university=uni))
    assert client.post(reverse("post_delete", args=[mine.pk])).status_code == 404
    client.force_login(ana)
    client.post(reverse("post_delete", args=[mine.pk]))
    client.force_login(UserFactory.create(role=User.Role.ADMIN))
    client.post(reverse("post_delete", args=[other.pk]))

    assert not Post.objects.exists()


@pytest.mark.django_db
def test_delete_requires_post(client: Client, ana: User) -> None:
    post = PostFactory.create(author=ana)
    client.force_login(ana)

    assert client.get(reverse("post_delete", args=[post.pk])).status_code == 405
    assert Post.objects.exists()


@pytest.mark.django_db
def test_script_in_a_post_is_not_executed(client: Client, ana: User) -> None:
    client.force_login(ana)
    client.post(reverse("post_create"), {"body": "<script>alert('xss')</script>"})
    post = Post.objects.get()

    html = client.get(reverse("post_detail", args=[post.pk])).content.decode()

    assert "<script>alert('xss')</script>" not in html
    assert "&lt;script&gt;" in html


def test_only_questions_can_be_anonymous(db: None) -> None:
    with pytest.raises(IntegrityError):
        PostFactory.create(is_anonymous=True, kind=Post.Kind.POST)
