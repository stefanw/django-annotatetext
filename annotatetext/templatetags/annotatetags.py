import re

from django import template
from django.template.defaultfilters import stringfilter, force_escape
from django.utils.safestring import mark_safe
from django.contrib.contenttypes.models import ContentType

from annotatetext.models import Annotation
from annotatetext.forms import NewAnnotationForm

register = template.Library()

@register.filter
@stringfilter
def simple_formatting(value):
    value = force_escape(value)
    value = value.replace("\r\n", "\n")
    value = "<p>%s</p>" % value
    value = re.sub("(?sum) - (.*?)\n", "<li> - \\1</li>\n", value)
    value = re.sub("(?sum) ([a-z0-9]+\)) (.*?)\n", "<li> \\1 \\2</li>\n", value)
    value = re.sub("(?sum)((?:<li>.*?</li>\n)+)", "</p><ul>\\1</ul><p>", value)
    value = re.sub("(?sum)\n\n", "\n\n</p><p>", value)
    value = re.sub("(?sum)</ul><p>(\s+)</p><ul>", "</ul>\\1<ul>", value)
    value = re.sub("(?sum)</p><p>(\s+)</p><p>", "\\1</p><p>", value)
    value = re.sub("(?sum)([^(?:</li>|</ul>|\n)])\n([^(?:</p>|<li>|\n</p>|<ul>)])", "\\1<br/>\n\\2", value)
    return mark_safe(value)

def find(f, seq):
  """Return first item in sequence where f(item) == True."""
  for item in seq:
    if f(item): 
      return item

@register.tag(name='get_latest_annotations')
def do_get_latest_annotations(parser, token):
    """ Use like so: {% get_latest_annotations as annotations [count=1]%}
    """
    as_var = None
    count = 1
    try:
        contents = token.split_contents()
        if len(contents) >= 2 and contents[1] == "as":
            as_var = contents[2]
        if len(contents) == 4:
            count = int(contents[3])
    except (ValueError, IndexError):
        raise template.TemplateSyntaxError, "Tag Syntax Error: %r as annotations [count=1]" % token.contents.split()[0]
    return LatestAnnotationsNode(as_var, count)

class LatestAnnotationsNode(template.Node):
    def __init__(self, as_var, count):
        self.as_var = as_var
        self.count = count

    def render(self, context):
         annotations = Annotation.objects.select_related("content_type").order_by("-timestamp")[:self.count]
         context[self.as_var] = annotations
         return ''
	
@register.tag(name='get_annotations_for')
def do_get_annotations_for(parser, token):
    """Use like so: {% get_annotations_for object_list as var_name %}
    Note: objects in object_list must be of one ContentType!
    var_name is a dict that contains the id of every object in object_list as key.
    The value is another dict with two keys: "annotations" as a list of annotations and
    "form" as an annotation form instance
    """
    as_var = None
    try:
        contents = token.split_contents()
        instance_name = contents[1]
        if len(contents) >= 4 and contents[2] == "as":
            as_var = contents[3]

    except (ValueError, IndexError):
        raise template.TemplateSyntaxError, "Tag Syntax Error: %r object_list as var_name" % token.contents.split()[0]
    return InsertAnnotationNode(instance_name, as_var)
    
class InsertAnnotationNode(template.Node):
    def __init__(self, instance_name, as_var):
        self.instance_var = template.Variable(instance_name)
        self.as_var = as_var
        
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
            # Avoid multiple queries, so get object from given list
            annotation.content_object = find(lambda x: x.id == annotation.object_id, instance_list)
            annotation_dict.setdefault(annotation.object_id, {})
            annotation_dict[annotation.object_id].setdefault("annotations", []).append(annotation)
        for instance in instance_list:
            annotation_dict.setdefault(instance.id, {})["form"] = NewAnnotationForm(auto_id=False, 
                initial={"content_type": ct.id, "object_id": instance.id})
        context[self.as_var] = annotation_dict
        return ""