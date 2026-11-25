from typing import TYPE_CHECKING, Any, ClassVar

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from core.markdown import render_markdown
from universities.models import Course, University

if TYPE_CHECKING:
    from accounts.models import User

BODY_MAX_LENGTH = 10_000


class PostQuerySet(models.QuerySet["Post"]):
    def visible_to(self, user: "User") -> "PostQuerySet":
        """The one place that decides who can read a post.

        Members see their own university's posts; nobody sees another university's.
        Hidden posts and posts by suspended authors are only visible to admins.
        """
        if user.is_platform_admin:
            return self
        if user.university_id is None:
            return self.none()
        return self.filter(
            university_id=user.university_id, is_hidden=False, author__is_active=True
        )


class Post(models.Model):
    class Kind(models.TextChoices):
        POST = "POST", _("Post")
        QUESTION = "QUESTION", _("Question")

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="posts"
    )
    university = models.ForeignKey(University, on_delete=models.PROTECT, related_name="posts")
    course = models.ForeignKey(
        Course,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="posts",
        verbose_name=_("course"),
    )
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.POST)
    title = models.CharField(_("title"), max_length=200, blank=True)
    body = models.TextField(_("text"), max_length=BODY_MAX_LENGTH)
    body_html = models.TextField(editable=False)  # sanitized render of `body`
    is_anonymous = models.BooleanField(_("anonymous"), default=False)
    is_hidden = models.BooleanField(_("hidden by a moderator"), default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = PostQuerySet.as_manager()

    class Meta:
        ordering = ("-created_at",)
        verbose_name = _("post")
        verbose_name_plural = _("posts")
        indexes: ClassVar = [models.Index(fields=("university", "-created_at"))]
        constraints: ClassVar = [
            models.CheckConstraint(
                condition=Q(is_anonymous=False) | Q(kind="QUESTION"),
                name="only_questions_can_be_anonymous",
            ),
        ]

    def __str__(self) -> str:
        return self.title or self.body[:60]

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.body_html = render_markdown(self.body)
        super().save(*args, **kwargs)

    def get_absolute_url(self) -> str:
        return reverse("post_detail", args=[self.pk])

    @property
    def is_question(self) -> bool:
        return self.kind == self.Kind.QUESTION

    @property
    def was_edited(self) -> bool:
        return (self.updated_at - self.created_at).total_seconds() > 60

    def can_edit(self, user: "User") -> bool:
        return user.pk == self.author_id

    def can_delete(self, user: "User") -> bool:
        return user.pk == self.author_id or user.is_platform_admin


MAX_IMAGES_PER_POST = 4


class PostImage(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="posts/", width_field="width", height_field="height")
    width = models.PositiveIntegerField(default=0)
    height = models.PositiveIntegerField(default=0)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("position", "pk")
        verbose_name = _("post image")
        verbose_name_plural = _("post images")

    def __str__(self) -> str:
        return str(self.image.name)


COMMENT_MAX_LENGTH = 2000


class CommentQuerySet(models.QuerySet["Comment"]):
    def visible_to(self, user: "User") -> "CommentQuerySet":
        visible = self.filter(post__in=Post.objects.visible_to(user))
        if user.is_platform_admin:
            return visible
        return visible.filter(is_hidden=False, author__is_active=True)


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="comments"
    )
    body = models.TextField(_("comment"), max_length=COMMENT_MAX_LENGTH)
    is_hidden = models.BooleanField(_("hidden by a moderator"), default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = CommentQuerySet.as_manager()

    class Meta:
        ordering = ("created_at",)
        verbose_name = _("comment")
        verbose_name_plural = _("comments")

    def __str__(self) -> str:
        return self.body[:60]

    def can_delete(self, user: "User") -> bool:
        return user.pk == self.author_id or user.is_platform_admin


class PostReaction(models.Model):
    """A "like". One per user per post; nobody can like their own post."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="post_reactions"
    )
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="reactions")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("reaction")
        verbose_name_plural = _("reactions")
        constraints: ClassVar = [
            models.UniqueConstraint(fields=("user", "post"), name="one_reaction_per_post"),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} ♥ {self.post_id}"
