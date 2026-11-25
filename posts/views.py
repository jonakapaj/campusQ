from django.contrib import messages
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from core.auth import AuthedRequest, verified_required
from posts.forms import CommentForm, PostForm
from posts.models import Comment, Post


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
    comments = Comment.objects.visible_to(request.user).filter(post=post).select_related("author")
    return render(
        request,
        "posts/detail.html",
        {"post": post, "comments": comments, "comment_form": CommentForm()},
    )


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


@require_POST
@verified_required
def comment_create(request: AuthedRequest, pk: int) -> HttpResponse:
    post = _visible_post(request, pk)
    if post.is_question:
        raise Http404  # questions get answers, not comments
    form = CommentForm(request.POST)
    htmx = request.headers.get("HX-Request") == "true"
    if not form.is_valid():
        if htmx:
            return render(request, "posts/_comment_form.html", {"post": post, "comment_form": form})
        messages.error(request, _("Write something first."))
        return redirect("post_detail", pk=post.pk)
    comment = form.save(commit=False)
    comment.post = post
    comment.author = request.user
    comment.save()
    if htmx:
        return render(
            request,
            "posts/_comment_created.html",
            {"post": post, "comment": comment, "comment_form": CommentForm()},
        )
    return redirect(f"{post.get_absolute_url()}#comment-{comment.pk}")


@require_POST
@verified_required
def comment_delete(request: AuthedRequest, pk: int) -> HttpResponse:
    comment = get_object_or_404(Comment.objects.visible_to(request.user), pk=pk)
    if not comment.can_delete(request.user):
        raise Http404
    comment.delete()
    if request.headers.get("HX-Request") == "true":
        return HttpResponse("")
    return redirect("post_detail", pk=comment.post_id)
