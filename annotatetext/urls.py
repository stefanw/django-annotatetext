from django.conf.urls.defaults import *
from feeds import LatestAnnotationsFeed, LatestAnnotationsFeedAtom

urlpatterns = patterns('',
    (r'^rss/$', LatestAnnotationsFeed(), {}, name="annotatetext-latest-rss"),
    (r'^atom/$', LatestAnnotationsFeedAtom(), {}, name="annotatetext-atom"),
    (r'^write/$', "annotatetext.views.post_annotation" , {}, 'annotatetext-post_annotation'),
    (r'^delete/$', "annotatetext.views.delete_annotation" , {}, 'annotatetext-delete_annotation'),
)