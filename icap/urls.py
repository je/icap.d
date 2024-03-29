#from django.conf.urls import patterns, url, include
from django.urls import path, include, re_path
from django.views.generic import RedirectView
from icap.views import *
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.cache import cache_page

urlpatterns = [
    path('', Index, name='index'),
    path('make-units/', Units, name='units'),
    path('feedback/', Feedback, name='feedback'),
    path('applicant/', ApplicantUpdate, name='applicant_update'),
    path('approvals/', Approvals, name='approvals'),
    re_path(r'^applicant/(?P<applicant_user_email>[^@\s]+@[^@\s]+\.[^@\s]+)/$', ApplicantDetail, name='applicant_detail'),
    re_path(r'^(?P<area_slug>[a-zA-Z0-9_\- ]+)/$', AreaDetail, name='area_detail'),
    re_path(r'^(?P<area_slug>[a-zA-Z0-9_\- ]+)/applicants/$', AreaApplicants, name='area_applicants'),
    re_path(r'^(?P<area_slug>[a-zA-Z0-9_\- ]+)/applicants/(?P<switch>reports)/$', AreaApplicantsReports, name='area_applicants_reports'),
    re_path(r'^(?P<area_slug>[a-zA-Z0-9_\- ]+)/applicants/(?P<switch>file-attachments)/$', AreaApplicantsReports, name='area_applicants_file-attachments'),
    re_path(r'^(?P<area_slug>[a-zA-Z0-9_\- ]+)/(?P<team_slug>[a-zA-Z0-9_\- ]+)/$', TeamDetail, name='team_detail'),
    re_path(r'^(?P<area_slug>[a-zA-Z0-9_\- ]+)/(?P<team_slug>[a-zA-Z0-9_\- ]+)/applicants/$', TeamApplicants, name='team_applicants'),
    re_path(r'^(?P<area_slug>[a-zA-Z0-9_\- ]+)/(?P<team_slug>[a-zA-Z0-9_\- ]+)/applicants/(?P<switch>reports)/$', TeamApplicantsReports, name='team_applicants_reports'),
    re_path(r'^(?P<area_slug>[a-zA-Z0-9_\- ]+)/(?P<team_slug>[a-zA-Z0-9_\- ]+)/applicants/(?P<switch>file-attachments)/$', TeamApplicantsReports, name='team_applicants_file-attachments'),
    re_path(r'^(?P<area_slug>[a-zA-Z0-9_\- ]+)/(?P<team_slug>[a-zA-Z0-9_\- ]+)/applicants/emails/$', TeamEmails, name='team_emails'),
    re_path(r'^(?P<area_slug>[a-zA-Z0-9_\- ]+)/(?P<team_slug>[a-zA-Z0-9_\- ]+)/applicants/approvals/$', TeamApprovals, name='team_approvals'),
    re_path(r'^(?P<area_slug>[a-zA-Z0-9_\- ]+)/(?P<team_slug>[a-zA-Z0-9_\- ]+)/(?P<position_slug>[a-zA-Z0-9_\- ]+)/$', PositionDetail, name='position_detail'),
]
