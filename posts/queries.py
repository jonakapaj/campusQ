"""Feed-ready post querysets: joins, prefetches and per-viewer annotations."""

from typing import Any

from django.db.models import Count, Exists, IntegerField, OuterRef, Prefetch, QuerySet, Subquery
from django.db.models.functions import Coalesce

from accounts.models import User
from posts.models import Comment, Post, PostQuerySet, PostReaction


def _count(queryset: QuerySet[Any]) -> Coalesce:
    # A correlated COUNT subquery per row: unlike Count() over two joins it can't
    # multiply rows, and it stays one query for the whole page.
    sub = (
        queryset.filter(post=OuterRef("pk"))
        .order_by()
        .values("post")
        .annotate(n=Count("pk"))
        .values("n")
    )
    return Coalesce(Subquery(sub, output_field=IntegerField()), 0)


def feed_posts(viewer: User) -> PostQuerySet:
    return (
        Post.objects.visible_to(viewer)
        .select_related("author", "author__university", "course", "university")
        .prefetch_related(Prefetch("images"))
        .annotate(
            like_count=_count(PostReaction.objects.all()),
            comment_count=_count(Comment.objects.visible_to(viewer)),
            liked=Exists(PostReaction.objects.filter(post=OuterRef("pk"), user=viewer)),
        )
    )
