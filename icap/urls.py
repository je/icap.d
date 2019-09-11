#from django.conf.urls import patterns, url, include
from django.urls import path, include, re_path
from django.views.generic import RedirectView
from icap.views import *
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.cache import cache_page

urlpatterns = [
    path('', Index, name='index'),
    path('feedback/', Feedback, name='feedback'),
    path('applicant/', ApplicantUpdate, name='applicant_update'),
    re_path(r'^applicant/(?P<applicant_user_email>[^@\s]+@[^@\s]+\.[^@\s]+)/$', ApplicantDetail, name='applicant_detail'),
    re_path(r'^(?P<area_slug>[a-zA-Z0-9_\- ]+)/$', AreaDetail, name='area_detail'),
    re_path(r'^(?P<area_slug>[a-zA-Z0-9_\- ]+)/(?P<team_slug>[a-zA-Z0-9_\- ]+)/$', TeamDetail, name='team_detail'),
    re_path(r'^(?P<area_slug>[a-zA-Z0-9_\- ]+)/(?P<team_slug>[a-zA-Z0-9_\- ]+)/(?P<position_slug>[a-zA-Z0-9_\- ]+)/$', PositionDetail, name='position_detail'),

    #re_path('build/wilderness/(?P<switch>full)', Build_Wilderness, name='wilderness_build_full'), #test
    #re_path('build/wilderness/(?P<switch>nodata)', Build_Wilderness, name='wilderness_build_nodata'), #test
    #re_path('build/wcm/(?P<switch>full)', Build_WCM, name='wcm_build_full'), #test
    #re_path('build/wcm/(?P<switch>nodata)', Build_WCM, name='wcm_build_nodata'), #test
]
