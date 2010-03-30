# -*- coding: utf-8 -*-
from difflib import SequenceMatcher

import django.dispatch
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
#from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django.conf import settings

from bundestagger.account.models import User

ANNOTATION_FLAGS = ("Erklärung", "Quelle?", "Quelle gefunden", "Querverweis", "Wichtig", "Faktisch falsch", "Formatierung/Fehler!", "Kommentar")

class Annotation(models.Model):
    timestamp = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, null=True, blank=True)
    content_type = models.ForeignKey(ContentType, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = generic.GenericForeignKey('content_type', 'object_id')
#    field_name = models.CharField(default="text", blank=False, max_length=100)
#   Make It more Simple, Stupid
    field_name = "text"
    selection_start = models.IntegerField()
    selection_end = models.IntegerField(blank=True, null=True)
    comment = models.TextField(blank=True)
    flags = models.SmallIntegerField()
    color = models.CharField(null=True, blank=True, max_length=100)
    
    _text = None
    
    update_signal = django.dispatch.Signal(providing_args=["content_object"])
    
    def __unicode__(self):
        return "Anmerkung an %s" % self.content_object

    def get_absolute_url(self):
        url = self.content_object.get_absolute_url()
        if "#" in url:
            url = url[:url.find("#")]
        return url+"#annotation-%d" % self.id

    def save(self, *args, **kwargs):
        super(Annotation, self).save(*args, **kwargs)
        if hasattr(self.content_object.__class__, "changed_signal"):
            self.content_object.__class__.changed_signal.connect(self.__class__.adapt_selections)

    @property 
    def is_footnote(self):
        if self.selection_end is None  or self.selection_start == self.selection_end:
            return True
        return False
        
    def footnote_part(self):
        return self.text[self.selection_start-10:self.selection_start]+"[X]"+self.text[self.selection_start:self.selection_start+10]

    @property
    def flag_value(self):
        return ANNOTATION_FLAGS[self.flags]

    @property
    def text(self):
        if self._text is None:
            self._text = unicode(getattr(self.content_object, self.field_name, None)).replace(u"\r\n",u"\n")
        return self._text
        
    @property
    def selection(self):
        return self.text[self.selection_range[0]:self.selection_range[1]]
        
    @property
    def selection_range(self):
        if self.selection_end is None:
            return (self.selection_start, self.selection_start)
        else:
            return (self.selection_start, self.selection_end)

    @classmethod
    def validate_selection(cls, text, start=0, end=None):
        if start < 0 or start > len(text):
            return False
        if end is not None and (end < start or end > len(text)):
            return False
        return True

    @classmethod
    def adapt_selections(cls, sender, **kwargs):
        s = SequenceMatcher(None, kwargs["old_text"], kwargs["new_text"])
        opcodes = s.get_opcodes()
        content_type = ContentType.objects.get_for_model(sender.__class__)
        annotations = cls.objects.filter(object_id=sender.id, content_type=content_type)
        for annotation in annotations:
            annotation.adapt_selection(opcodes, len(kwargs["new_text"]))
            annotation.save()
    
    def adapt_selection(self, opcodes, textlen):
        m = [self.selection_start, self.selection_end]
        for opcode in opcodes:
            if opcode[0] == "insert" and opcode[1]>=m[0] and opcode[1]<m[1]:
                m[1] = m[1] + (opcode[4] - opcode[3])
            elif opcode[0] == "insert" and opcode[1]<m[0]:
                m[0] = m[0] + (opcode[4] - opcode[3])
                m[1] = m[1] + (opcode[4] - opcode[3])
            if opcode[0] == "delete" and (opcode[1]>=m[0] and opcode[2]<m[1]):
                # delete in marking
                m[1] = m[1] - (opcode[2] - opcode[1])
            elif opcode[0] == "delete" and (opcode[1]>=m[0] and opcode[2]>=m[1]):
                # delete rear part of the marking
                m[1] = m[1] - (m[1] - opcode[1])
            elif opcode[0] == "delete" and (opcode[1]<=m[0] and opcode[2]>=m[1]):
                # delete all of the marking
                m[0] = opcode[1]
                m[1] = opcode[1]
            elif opcode[0] == "delete" and (opcode[1]<m[0] and opcode[2]<m[0]):
                # delete before marking
                m[0] = m[0] - (opcode[2] - opcode[1])
                m[1] = m[1] - (opcode[2] - opcode[1])
            elif opcode[0] == "delete" and (opcode[1]<m[0] and opcode[2]<m[1] and opcode[2]>=m[0]):
                # delete front part of marking
                m[1] = m[1] - (m[0]- opcode[2])
                m[0] = m[0] - (m[0]- opcode[1])
        self.selection_start = max(0, m[0])
        self.selection_end = min(textlen, m[1])