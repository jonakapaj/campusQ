from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class PostsConfig(AppConfig):
    name = "posts"
    verbose_name = _("Posts")

    def ready(self) -> None:
        from posts import signals  # noqa: F401  (connects the receivers)
