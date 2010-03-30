from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.http import Http404, HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, HttpResponseNotAllowed
from django.template import RequestContext, loader, Context
from forms import NewAnnotationForm
from models import Annotation
from bundestagger.account.auth import is_post, logged_in, get_user

@is_post
def post_annotation(request):
    form = NewAnnotationForm(request.POST)
    fragment = ""
    if form.is_valid():
        new_annotation = Annotation(content_type=form.cleaned_data["content_type"],
                    object_id=form.cleaned_data["object_id"],
                    selection_start=form.cleaned_data["selection_start"],
                    selection_end=form.cleaned_data["selection_end"],
                    comment=form.cleaned_data["comment"],
                    flags=form.cleaned_data["flags"],
                    color=form.cleaned_data["color"])
        new_annotation.user = get_user(request)
        new_annotation.save()
        fragment = "#annotation-%d" % new_annotation.id
        if hasattr(new_annotation.content_object.__class__, "connected_update"):
            Annotation.update_signal.connect(new_annotation.content_object.__class__.connected_update)
        Annotation.update_signal.send(sender=new_annotation, content_object=new_annotation.content_object)
        if request.is_ajax():
            t = loader.get_template("annotatetext/_annotation.html")
            own_context = {"annotation": new_annotation, "speech_part": new_annotation.content_object}
            return HttpResponse(t.render(RequestContext(request, own_context)))
        else:
            next = "/"
            if "next" in request.POST:
                next = request.POST["next"]
            return redirect(next+fragment)
    else:
        if not request.is_ajax():
            messages.add_message(request, messages.INFO, u"Fehler bei Anmerkung!")
        return HttpResponseBadRequest()

@is_post
@logged_in
def delete_annotation(request):
    if not request.bundesuser.is_admin:
        return HttpResponseForbidden()
    if not "annoid" in request.POST:
        return HttpResponseBadRequest()
    try:
        annoid = int(request.POST["annoid"])
    except TypeError:
        return HttpResponseBadRequest()
    annotation = get_object_or_404(Annotation, id=annoid)
    annotation.delete()
    Annotation.update_signal.send(sender=annotation, content_object=annotation.content_object)
    next = "/"
    if "next" in request.POST:
        next = request.POST["next"]
    return redirect(next)