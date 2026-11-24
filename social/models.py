from typing import ClassVar

from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.utils.translation import gettext_lazy as _

from universities.models import Course


class UserFollow(models.Model):
    follower = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="following_links"
    )
    followed = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="follower_links"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("user follow")
        verbose_name_plural = _("user follows")
        constraints: ClassVar = [
            models.UniqueConstraint(fields=("follower", "followed"), name="user_follow_once"),
            models.CheckConstraint(
                condition=~Q(follower=F("followed")), name="user_cannot_follow_self"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.follower_id} → {self.followed_id}"


class CourseFollow(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="course_follows"
    )
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="follows")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("course follow")
        verbose_name_plural = _("course follows")
        constraints: ClassVar = [
            models.UniqueConstraint(fields=("user", "course"), name="course_follow_once"),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} → course {self.course_id}"
