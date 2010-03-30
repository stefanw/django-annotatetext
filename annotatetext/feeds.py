# -*- coding: utf-8 -*-
from django.contrib.syndication.feeds import Feed
from django.utils.feedgenerator import Atom1Feed

from models import Annotation

class LatestAnnotationsFeed(Feed):
    title = "Anmerkungen auf BundesTagger"
    link = "/"
    description = "Letzte Anmerkungen zu Plenarprotokollen des Deutschen Bundestages auf BundesTagger.de"
    description_template = "annotatetext/annotation_description.html"

    def items(self):
        return Annotation.objects.order_by('-timestamp')[:5]
        
class LatestAnnotationsFeedAtom(LatestAnnotationsFeed):
    feed_type = Atom1Feed
    subtitle = LatestAnnotationsFeed.description