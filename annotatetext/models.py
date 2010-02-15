# -*- coding: utf-8 -*-
from difflib import SequenceMatcher

from django import dispatch
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django.conf import settings

ANNOTATION_FLAGS = getattr(settings, "ANNOTATETEXT_FLAGS", (_("Annotation"), ))


class Annotation(models.Model):
    """
    >>> from otherapp.models import ToBeAnnotated
    >>> tba = ToBeAnnotated(text="There should be one-- and preferably only \
    one --obvious way to do it.")
    >>> tba.save()
    >>> a = Annotation.objects.create(content_object=tba, field_name="text", \
    selection_start=22, selection_end=45,\
        comment=u"This is the Python way")
    >>> a.selection
    u'and preferably only one'
    >>> a.selection_range
    (22, 45)
    >>> tba.text = "There should be at least one-- and preferably not so \
    many --obvious ways to do it."
    >>> tba.save()
    >>> a = Annotation.objects.get(id=a.id) #force reload of content_object
    >>> a.selection
    u'and preferably not so many'
    >>> a.selection_range
    (31, 57)
    """
    user = models.ForeignKey(User, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now=True)
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey('content_type', 'object_id')
    field_name = models.CharField(blank=True, null=True, max_length=100)
    selection_start = models.IntegerField()
    selection_end = models.IntegerField(blank=True, null=True)
    comment = models.TextField(blank=True)
    flags = models.SmallIntegerField(default=0)
    color = models.CharField(null=True, blank=True, max_length=100)

    _text = None # Text cache

    def __unicode__(self):
        return _(u"Annotation on '%s'") % self.content_object

    def get_absolute_url(self):
        url = self.content_object.get_absolute_url()
        if "#" in url:
            # URL already has an anchor in it, don't modify
            return url
        return url+"#annotation-%d" % self.id

    def save(self, *args, **kwargs):
        self._text = None
        super(Annotation, self).save(*args, **kwargs)
        if hasattr(self.content_object.__class__, \
            "annotatetext_changed_signal"):
            # content_object may define a signal in its model like so:
            # annotatetext_changed_signal = django.dispatch.Signal(\
            #    providing_args=["old_text", "new_text"])
            # send the signal whenever text changes
            self.content_object.__class__.annotatetext_changed_signal.\
                connect(self.__class__.adapt_selections)
        else:
            # Workaround if custom signal cannot be detected
            def wrap_temp_store_textfield(sender, instance, **kwargs):
                return Annotation.temp_store_textfield(sender, instance, \
                    self.field_name)

            def wrap_retrieve_old_textfield(sender, instance, created, \
                **kwargs):
                return Annotation.retrieve_old_textfield(sender, \
                    instance, created, self.field_name)
            models.signals.pre_save.connect(wrap_temp_store_textfield,
                sender=self.content_object.__class__, weak=False)
            models.signals.post_save.connect(wrap_retrieve_old_textfield,
                sender=self.content_object.__class__, weak=False)

    @classmethod
    def temp_store_textfield(cls, sender, instance, field_name):
        if instance.pk is not None:
            old_object = sender._default_manager.get(pk=instance.pk)
            instance._annotatetext_old_text = cls.\
                get_textfield_from_object(old_object, field_name=field_name)

    @classmethod
    def retrieve_old_textfield(cls, sender, instance, created, field_name):
        if not created and hasattr(instance, "_annotatetext_old_text"):
            old_text = instance._annotatetext_old_text
            new_text = cls.get_textfield_from_object(instance, field_name)
            cls.adapt_selections(instance,
                old_text=old_text, new_text=new_text)

    @property
    def is_footnote(self):
        if self.selection_end is None or \
            self.selection_start == self.selection_end:
            return True
        return False

    def footnote_part(self):
        return self.text[self.selection_start-10:self.selection_start]+\
            "[X]"+self.text[self.selection_start:self.selection_start+10]

    @property
    def flag_value(self):
        return ANNOTATION_FLAGS[self.flags]

    def clean_text(self, text):
        text = text.replace(u"\r\n", u"\n")
        return text

    @classmethod
    def get_textfield_from_object(cls, obj, field_name="text"):
        if field_name is None:
            return unicode(getattr(obj, "text", ""))
        else:
            return unicode(getattr(obj, field_name, ""))

    @property
    def text(self):
        if self._text is None:
            self._text = Annotation.\
                get_textfield_from_object(self.content_object,
                    field_name=self.field_name)
        self._text = self.clean_text(self._text)
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
        annotations = Annotation.objects.filter(object_id=sender.id,
            content_type=content_type)
        for annotation in annotations:
            annotation.adapt_selection(opcodes)
            annotation.save()

    def adapt_selection(self, opcodes):
        m = [self.selection_start, self.selection_end]
        for opcode in opcodes:
            if opcode[0] == "insert" and opcode[1]>=m[0] and opcode[1]<m[1]:
                m[1] = m[1] + (opcode[4] - opcode[3])
            elif opcode[0] == "insert" and opcode[1]<m[0]:
                m[0] = m[0] + (opcode[4] - opcode[3])
                m[1] = m[1] + (opcode[4] - opcode[3])
            if opcode[0] == "delete" and \
                (opcode[1]>=m[0] and opcode[2]<m[1]):
                # delete in marking
                m[1] = m[1] - (opcode[2] - opcode[1])
            elif opcode[0] == "delete" and \
                (opcode[1]>=m[0] and opcode[2]>=m[1]):
                # delete rear part of the marking
                m[1] = m[1] - (m[1] - opcode[1])
            elif opcode[0] == "delete" and \
                (opcode[1]<=m[0] and opcode[2]>=m[1]):
                # delete all of the marking
                m[0] = opcode[1]
                m[1] = opcode[1]
            elif opcode[0] == "delete" and \
                (opcode[1]<m[0] and opcode[2]<m[0]):
                # delete before marking
                m[0] = m[0] - (opcode[2] - opcode[1])
                m[1] = m[1] - (opcode[2] - opcode[1])
            elif opcode[0] == "delete" and \
                (opcode[1]<m[0] and opcode[2]<m[1] and opcode[2]>=m[0]):
                # delete front part of marking
                m[1] = m[1] - (m[0]- opcode[2])
                m[0] = m[0] - (m[0]- opcode[1])
        self.selection_start = m[0]
        self.selection_end = m[1]
