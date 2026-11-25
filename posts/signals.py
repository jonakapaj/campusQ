from typing import Any

from django.db.models.signals import post_delete
from django.dispatch import receiver

from posts.models import PostImage


@receiver(post_delete, sender=PostImage)
def delete_image_file(sender: type[PostImage], instance: PostImage, **kwargs: Any) -> None:
    # Runs for cascades too (deleting a post or a whole account removes the files).
    instance.image.delete(save=False)
