from django.contrib import messages
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from core.auth import AuthedRequest, verified_required
from posts.forms import PostForm
from posts.models import Post


def _visible_post(request: AuthedRequest, pk: int) -> Post:
    return get_object_or_404(
        Post.objects.visible_to(request.user)
        .select_related("author", "author__university", "course", "university")
        .prefetch_related("images"),
        pk=pk,
    )


@verified_required
def post_create(request: AuthedRequest) -> HttpResponse:
    if request.user.university_id is None:
        messages.error(request, _("Only members of a university can post."))
        return redirect("home")
    initial = {"course": request.GET.get("course")}
    form = PostForm(
        request.POST or None, request.FILES or None, author=request.user, initial=initial
    )
    if request.method == "POST" and form.is_valid():
        post = form.save()
        return redirect("post_detail", pk=post.pk)
    return render(request, "posts/form.html", {"form": form, "editing": False})


@verified_required
def post_detail(request: AuthedRequest, pk: int) -> HttpResponse:
    post = _visible_post(request, pk)
    return render(request, "posts/detail.html", {"post": post})


@verified_required
def post_edit(request: AuthedRequest, pk: int) -> HttpResponse:
    post = _visible_post(request, pk)
    if not post.can_edit(request.user):
        raise Http404
    form = PostForm(request.POST or None, instance=post, author=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Saved."))
        return redirect("post_detail", pk=post.pk)
    return render(request, "posts/form.html", {"form": form, "editing": True, "post": post})


@require_POST
@verified_required
def post_delete(request: AuthedRequest, pk: int) -> HttpResponse:
    post = _visible_post(request, pk)
    if not post.can_delete(request.user):
        raise Http404
    post.delete()
    messages.success(request, _("Deleted."))
    return redirect("home")
