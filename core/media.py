"""Serve uploaded files only to people allowed to see them.

A path is served only if it is exactly the stored name of an avatar of an active
user, or of an image of a post the requester can see. Anything else, including
"../" tricks, is a 404: we never map a URL straight onto the filesystem.
"""

from django.core.files.storage import default_storage
from django.http import FileResponse, Http404, HttpResponseBase

from accounts.models import User
from core.auth import AuthedRequest, verified_required
from posts.models import Post, PostImage


def _allowed(request: AuthedRequest, path: str) -> bool:
    if path.startswith("avatars/"):
        return User.objects.filter(avatar=path, is_active=True).exists()
    if path.startswith("posts/"):
        return PostImage.objects.filter(
            image=path, post__in=Post.objects.visible_to(request.user)
        ).exists()
    return False


@verified_required
def media(request: AuthedRequest, path: str) -> HttpResponseBase:
    if not _allowed(request, path) or not default_storage.exists(path):
        raise Http404
    response = FileResponse(default_storage.open(path, "rb"), content_type="image/webp")
    # Private: shared caches and proxies must not keep a copy.
    response["Cache-Control"] = "private, max-age=86400"
    response["Content-Disposition"] = "inline"
    return response
