import re

from django import forms
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy as _

from annotatetext.models import Annotation, ANNOTATION_FLAGS

class NewAnnotationForm(forms.Form):
    selection_start = forms.IntegerField(required=True)
    selection_end = forms.IntegerField(required=True)
    flags = forms.ChoiceField(choices=enumerate(ANNOTATION_FLAGS),widget=forms.Select(attrs={"class":"annotationflagselect"}), required=True)
    content_type = forms.IntegerField(widget=forms.HiddenInput, required=True)
    object_id = forms.IntegerField(widget=forms.HiddenInput, required=True)
    comment = forms.CharField(widget=forms.Textarea(attrs={'cols': 50, 'rows': 3}), required=False)
    color = forms.CharField(initial="#3f0b5c", widget=forms.TextInput(attrs={"size":6}), required=False)
    lengthcheck = forms.IntegerField(widget=forms.HiddenInput, required=True)
            
    def clean_color(self):
        data = self.cleaned_data["color"]
        data = data.lower()
        if re.match("^#([0-9a-f]{3}|[0-9a-f]{6})$", data) is None:
            raise forms.ValidationError(_("Bogus color"))
        return data
        
    def clean_flags(self):
        flags = self.cleaned_data["flags"]
        flags = int(flags)
        if not flags in range(len(ANNOTATION_FLAGS)):
            raise forms.ValidationError(_("Bogus Flag"))
        return flags
        
    def clean(self):
        cleaned_data = self.cleaned_data
        content_type_id = cleaned_data.get("content_type", None)
        object_id = cleaned_data.get("object_id", None)
        if content_type_id is None or object_id is None:
            raise forms.ValidationError(_("Missing Parameter"))
        try:
            ct = ContentType.objects.get(id=content_type_id)
        except ContentType.DoesNotExist:
            raise forms.ValidationError(_("Bogus content"))
        try:
            obj = ct.get_object_for_this_type(id=object_id)
        except ct.model_class().DoesNotExist:
            raise forms.ValidationError(_("Bogus object"))
        cleaned_data["content_type"] = ct
        # Connected Model must have attribute annotatable set to True, 
        # so not every model can be annotated, don't know if this is cool in practice
        if not getattr(obj, "annotatable", False):
            raise forms.ValidationError(_("Invalid object"))
        if not hasattr(obj,Annotation.field_name):
            raise forms.ValidationError(_("Bogus object"))
        text = getattr(obj, Annotation.field_name)
        if len(text) != cleaned_data["lengthcheck"]:
            raise forms.ValidationError(_("Text changed"))
        if not "selection_start" in cleaned_data or not "selection_end" in cleaned_data:
            raise forms.ValidationError(_("Missing Parameter for selection"))
        if not Annotation.validate_selection(text, start=cleaned_data["selection_start"], end=cleaned_data["selection_end"]):
            raise forms.ValidationError(_("Bogus selection"))
        # disallow footnotes? uncomment following
#        if cleaned_data["selection_end"] == cleaned_data["selection_start"]:
#            raise forms.ValidationError(_("No Selection"))
        if "flags" not in cleaned_data or "selection_start" not in cleaned_data:
            raise forms.ValidationError(_("Missing parameters"))
        return cleaned_data
