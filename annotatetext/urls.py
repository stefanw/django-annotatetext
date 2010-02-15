from django.conf.urls.defaults import *

urlpatterns = patterns('',
    (r'^write/$', "annotatetext.views.post_annotation" , {}, 'annotatetext-post_annotation'),
    (r'^delete/$', "annotatetext.views.delete_annotation" , {}, 'annotatetext-delete_annotation'),
)