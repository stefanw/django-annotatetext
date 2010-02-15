from django.shortcuts import render_to_response
from django.template import RequestContext
from models import ToBeAnnotated

def index(request):
    tbas = ToBeAnnotated.objects.all()
    return render_to_response("index.html",RequestContext(request, {"tbas":tbas}))
