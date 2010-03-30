from django import template
from django.contrib.contenttypes.models import ContentType
from django.utils.itercompat import groupby

from annotatetext.models import *
from annotatetext.forms import NewAnnotationForm

register = template.Library()

def find(f, seq):
  """Return first item in sequence where f(item) == True."""
  for item in seq:
      if f(item):
          return item

@register.tag(name='get_latest_annotations')
def do_get_latest_annotations(parser, token):
    """
    """
    as_var = None
    try:
        contents = token.split_contents()
        if len(contents) >= 2 and contents[1] == "as":
            as_var = contents[2]
    except (ValueError, IndexError):
        raise template.TemplateSyntaxError, "%r tag requires two arguments" % token.contents.split()[0]
    return LatestAnnotationsNode(as_var)

class LatestAnnotationsNode(template.Node):
    def __init__(self, as_var):
        self.as_var = as_var

    def render(self, context):
        # be nice and don't show errors on front page
         annotations = Annotation.objects.select_related("content_type").filter(flags__in=[0,1,2,3,4,5,7]).order_by("-timestamp")[:1]
         if len(annotations)==0:
             context[self.as_var] = []
             return ''
         object_ids = [a.object_id for a in annotations]
         model = annotations[0].content_type.model_class()
         annotated = model.objects.filter(id__in=object_ids).select_related("speech", "speech__speaker", "speech__speaker__party")
         for annotation in annotations:
             annotation.annotated = find(lambda x: x.id == annotation.object_id, annotated)
             annotation.annotated_text = annotation.annotated.text[annotation.selection_start:annotation.selection_end]
         context[self.as_var] = annotations
         return ''
	
@register.tag(name='get_annotations_for')
def do_get_annotations_for(parser, token):
    """
    """
    as_var = None
    form_var = None
    try:
        contents = token.split_contents()
        instance_name = contents[1]
        if len(contents) >= 4 and contents[2] == "as":
            as_var = contents[3]
        if len(contents) >= 5:
            form_var = contents[4]

    except (ValueError, IndexError):
        raise template.TemplateSyntaxError, "%r tag requires two or three arguments" % token.contents.split()[0]
    return InsertAnnotationNode(instance_name, as_var, form_var)
    
class InsertAnnotationNode(template.Node):
    def __init__(self, instance_name, as_var, form_var):
        self.instance_var = template.Variable(instance_name)
        self.as_var = as_var
        self.form_var = form_var
        
    def render(self, context):
        try:
            instance_list = self.instance_var.resolve(context)
        except template.VariableDoesNotExist:
            return ''
        if len(instance_list) == 0:
            return ''
        ct = ContentType.objects.get_for_model(instance_list[0])
        annotations = Annotation.objects.filter(content_type=ct, object_id__in=[o.id for o in instance_list])\
            .select_related("user").order_by("object_id", "selection_start", "-selection_end")
        annotation_dict = {}
        for annotation in annotations:
            annotation.content_object = find(lambda x: x.id == annotation.object_id, instance_list)
            annotation_dict.setdefault(annotation.object_id, {})
            annotation_dict[annotation.object_id].setdefault("annotations", []).append(annotation)
        for instance in instance_list:
            annotation_dict.setdefault(instance.id, {})["form"] = NewAnnotationForm(auto_id=False, initial={"content_type": ct.id, "object_id": instance.id})
        context[self.as_var] = annotation_dict
        return ""