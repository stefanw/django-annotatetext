from django.shortcuts import get_object_or_404
from django.http import Http404, HttpResponseRedirect, HttpResponseBadRequest, \
    HttpResponseForbidden, HttpResponseNotAllowed

from annotatetext.forms import NewAnnotationForm
from annotatetext.models import Annotation

def post_annotation(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    form = NewAnnotationForm(request.POST)
    if form.is_valid():
        new_annotation = Annotation(content_type=form.cleaned_data["content_type"],
                    object_id=form.cleaned_data["object_id"],
                    user=request.user,
                    selection_start=form.cleaned_data["selection_start"],
                    selection_end=form.cleaned_data["selection_end"],
                    comment=form.cleaned_data["comment"],
                    flags=form.cleaned_data["flags"],
                    color=form.cleaned_data["color"])
        new_annotation.save()
        fragment = "#annotation-%d" % new_annotation.id
        return HttpResponseRedirect(request.POST.get("next","/") + fragment)
    else:
        return HttpResponseBadRequest()

def delete_annotation(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    if not request.user.is_staff:
        return HttpResponseForbidden()
    if not "annotation_id" in request.POST:
        return HttpResponseBadRequest()
    try:
        annoid = int(request.POST["annotation_id"])
    except (TypeError, ValueError):
        return HttpResponseBadRequest()
    annotation = get_object_or_404(Annotation, id=annoid)
    annotation.delete()
    return HttpResponseRedirect(request.POST.get("next","/"))