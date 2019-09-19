from django.template import Context, loader, RequestContext
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.views.generic.edit import CreateView, DeleteView, UpdateView

from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q, F, Max, Min, Count, Avg, Sum
from django.contrib import messages
from icap.models import *
from icap.forms import *
from django.contrib.auth.models import User, Group
import datetime
from datetime import timedelta
from django.forms.models import inlineformset_factory
from django.forms.formsets import formset_factory
from ftplib import FTP
import urllib.request as urlreq
from xml.dom import minidom
from django.contrib.gis import geos
from django.contrib.gis.geos import *
from django.contrib.gis.measure import D, Area
from django.contrib.gis.db.models import Extent, Union, Collect
from decimal import Decimal
from dateutil.relativedelta import relativedelta
import calendar
import zipfile
import os
#from django.core.urlresolvers import reverse_lazy
from django.urls import reverse_lazy
#from django.views.decorators.cache import cache_page
from guardian.shortcuts import assign, get_users_with_perms, get_objects_for_user, remove_perm
from django.core.mail import send_mail, send_mass_mail
from django.core.mail import EmailMultiAlternatives

def Feedback(request):
    when = datetime.datetime.now()
    if request.method == 'POST':
        form = FeedbackForm(request.POST)
        if form.is_valid():
            fn = form.cleaned_data['firstname']
            ln = form.cleaned_data['lastname']
            em = form.cleaned_data['email']
            fm = form.cleaned_data['feedback']
            mailfrom = 'feedback@' + request.get_host()
            # fm = str(form)
            mtxt = "Feedback from user. \r\n" + fn +"\r\n" + ln +"\r\n" + em +"\r\n" + fm +"\r\n"
            mhtm = "Feedback from user. <br/><br/>" + fn + "<br/>" + ln + "<br/>" + em + "<br/>" + fm + "<br/>"
            msg = EmailMultiAlternatives('Feedback from user', mtxt, mailfrom, [mailfrom,])
            msg.attach_alternative(mhtm, "text/html")
            msg.send()
            m = 'Feedback sent. Thank your for your comment or complaint.'
            messages.success(request, m)
            return HttpResponseRedirect('/')
    else:
        form = FeedbackForm()

    return render(request,'icap/event_map.html', { 'when': when, 'form': form, })

from django.contrib.auth.signals import user_logged_in, user_logged_out

def update_user_login(sender, user, **kwargs):
    msg = 'User %s login successful.' % (user)
    l = Logitem(author=user, status='S', message=msg, obj_model='Session', obj_id='', obj_in='', obj_out='',)
    l.save()
    if not user.has_perm('icap.add_applicant'):
        assign('icap.add_applicant',user)
    #user.userlogin_set.create(timestamp=timezone.now())
    #user.save()

user_logged_in.connect(update_user_login)

def Index(request):
    areas = AreaUS.objects.exclude(deleted=True)
    return render(request, 'index.html', {'areas': areas,})

def AreaDetail(request, area_slug):
    area_ = get_object_or_404(AreaUS, slug__iexact=area_slug)
    if request.method == "POST":
        if "areastatus" in request.POST:
            open_date = request.POST.get('open')
            close_date = request.POST.get('close')
            status = AreaUS.objects.filter(slug__iexact=area_slug).update(author=request.user, open_date=open_date, close_date=close_date)
            msg = 'Open/close dates for <a class=\"alert-link\" href=\"/%s/">%s</a> updated by %s. Position dates override team dates, team dates override area dates.' % (area.slug, area, request.user.email)
            messages.success(request, msg)
            l = Logitem(author=request.user, status='S', message=msg, obj_model='Area', obj_id=area.id, obj_in='', obj_out='',)
            l.save()
            return HttpResponseRedirect('/%s/' % (area.slug))
    area_teams = Team.objects.filter(
        Q(area__slug__iexact=area_slug)
        ).exclude(deleted=True)
    return render(request,'icap/area.html', {'area': area_, 'area_teams': area_teams,})

def TeamDetail(request, area_slug, team_slug):
    team = get_object_or_404(Team, Q(area__slug=area_slug), slug__iexact=team_slug)
    if request.method == "POST":
        if "teamstatus" in request.POST:
            open_date = request.POST.get('open')
            close_date = request.POST.get('close')
            status = Team.objects.filter(Q(area__slug=area_slug, slug__iexact=team_slug)).update(author=request.user, open_date=open_date, close_date=close_date)
            msg = 'Open/close dates for <a class=\"alert-link\" href=\"/%s/%s/">%s %s</a> updated by %s. Position dates override team dates, team dates override area dates.' % (team.area.slug, team.slug, team.area, team, request.user.email)
            messages.success(request, msg)
            l = Logitem(author=request.user, status='S', message=msg, obj_model='Team', obj_id=team.id, obj_in='', obj_out='',)
            l.save()
            return HttpResponseRedirect('/%s/%s/' % (team.area.slug, team.slug))
    team_positions = Position.objects.filter(
        Q(team__slug__iexact=team_slug),
        Q(team__area__slug__iexact=area_slug)
        ).exclude(deleted=True)
    return render(request,'icap/area_team.html', {'team': team, 'team_positions': team_positions,})

def PositionDetail(request, area_slug, team_slug, position_slug):
    position = get_object_or_404(Position, Q(team__area__slug=area_slug), Q(team__slug=team_slug), slug__iexact=position_slug)
    #position.popen = PositionStatus.objects.filter(
    #    Q(position__slug__iexact=position_slug),
    #    Q(position__team__slug__iexact=team_slug),
    #    Q(position__team__area__slug__iexact=area_slug),
    #    Q(status__iexact='O')
    #    ).latest('modified')
    #position.pclose = PositionStatus.objects.filter(
    #    Q(position__slug__iexact=position_slug),
    #    Q(position__team__slug__iexact=team_slug),
    #    Q(position__team__area__slug__iexact=area_slug),
    #    Q(status__iexact='C')
    #    ).latest('modified')
    position_applications = Application.objects.filter(
        Q(position__slug__iexact=position_slug),
        Q(position__team__slug__iexact=team_slug),
        Q(position__team__area__slug__iexact=area_slug)
        ).exclude(deleted=True)

    if request.user.is_authenticated:
        applicant, _ = Applicant.objects.get_or_create(author__email__iexact=request.user.email, defaults={'author_id': request.user.id})
        try:
            position_application = Application.objects.get(
                Q(position__slug__iexact=position_slug),
                Q(position__team__slug__iexact=team_slug),
                Q(position__team__area__slug__iexact=area_slug),
                Q(applicant__author__email__iexact=request.user.email),
                ~Q(deleted=True)
                )
        except Application.DoesNotExist:
            position_application = None
    else:
        applicant = None
        position_application = None

    if request.method == "POST":
        if "applications" in request.POST:
            for app in position_applications:
                app_form = 'application_status_' + str(app.id)
                if app_form in request.POST:
                    app_status = request.POST.get(app_form,'')
                    set_status = ApplicationStatus.objects.create(author=request.user, application=app, status=app_status, effective=datetime.datetime.now())
                    app.status = app_status
                    ok = Application.objects.filter(id=app.id).update(status=app_status)
                    msg = 'Application for %s to <a class=\"alert-link\" href=\"/%s/%s/%s/\">%s %s %s</a> updated by %s.' % (app.applicant.author.email, position.team.area.slug, position.team.slug, position.slug, position.team.area, position.team, position, request.user.email)
                    messages.success(request, msg)

            msg = '%s applications to <a class=\"alert-link\" href=\"/%s/%s/%s/\">%s %s %s</a> updated by %s.' % (position_applications.count(), position.team.area.slug, position.team.slug, position.slug, position.team.area, position.team, position, request.user.email)
            messages.success(request, msg)
            l = Logitem(author=request.user, status='S', message=msg, obj_model='ApplicationStatus', obj_id='', obj_in='', obj_out='',)
            l.save()
            return HttpResponseRedirect('/%s/%s/%s/' % (position.team.area.slug, position.team.slug, position.slug))
        else:
            for app in position_applications:
                app_button = 'app_' + str(app.id)
                if app_button in request.POST:
                    app_form = 'application_status_' + str(app.id)
                    if app_form in request.POST:
                        app_status = request.POST.get(app_form,'')
                        set_status = ApplicationStatus.objects.create(author=request.user, application=app, status=app_status, effective=datetime.datetime.now())
                        app.status = app_status
                        ok = Application.objects.filter(id=app.id).update(status=app_status)
                        msg = 'Application for %s to <a class=\"alert-link\" href=\"/%s/%s/%s/\">%s %s %s</a> updated by %s.' % (app.applicant.author.email, position.team.area.slug, position.team.slug, position.slug, position.team.area, position.team, position, request.user.email)
                        messages.success(request, msg)
                        l = Logitem(author=request.user, status='S', message=msg, obj_model='ApplicationStatus', obj_id='', obj_in='', obj_out='',)
                        l.save()
                        return HttpResponseRedirect('/%s/%s/%s/' % (position.team.area.slug, position.team.slug, position.slug))


        if "positionstatus" in request.POST:
            open_date = request.POST.get('open')
            close_date = request.POST.get('close')
            open_status = PositionStatus.objects.create(author=request.user, position=position, status='O', effective=open_date)
            close_status = PositionStatus.objects.create(author=request.user, position=position, status='C', effective=close_date)
            position.open_date = open_status.effective
            position.close_date = close_status.effective
            position.save()
            msg = 'Open/close dates for <a class=\"alert-link\" href=\"/%s/%s/%s/\">%s %s %s</a> updated by %s. Position dates override team dates, team dates override area dates.' % (position.team.area.slug, position.team.slug, position.slug, position.team.area, position.team, position, request.user.email)
            messages.success(request, msg)
            l = Logitem(author=request.user, status='S', message=msg, obj_model='Position', obj_id=position.id, obj_in='', obj_out='',)
            l.save()
            return HttpResponseRedirect('/%s/%s/%s/' % (position.team.area.slug, position.team.slug, position.slug))

        if position_application:
            form = ApplicationForm(request.POST, instance=position_application)
        else:
            form = ApplicationForm(request.POST)
        if form.is_valid():
            valid_application = form.save(commit=False)
            valid_application.position_id = position.id
            valid_application.applicant_id = applicant.id
            valid_application.author_id = request.user.id
            valid_application.save()
            form.save_m2m()
            msg = 'Application to <a class=\"alert-link\" href=\"/%s/%s/%s/\">%s %s %s</a> for <a class=\"alert-link\" href=\"/applicant/%s/\">%s</a> updated.' % (position.team.area.slug, position.team.slug, position.slug, position.team.area, position.team, position, valid_application.applicant.author.email, valid_application.applicant.author.email)
            messages.success(request, msg)
            l = Logitem(author=request.user, status='S', message=msg, obj_model='Applicant', obj_id=valid_application.id, obj_in='', obj_out='',)
            l.save()
            return HttpResponseRedirect('/applicant/%s/' % (applicant.author.email))
    else:
        if position_application:
            form = ApplicationForm(instance=position_application)
        else:
            form = ApplicationForm()

    return render(request,'icap/area_team_position.html', {'position': position, 'position_applications': position_applications, 'applicant': applicant, 'position_application': position_application, 'form': form,})

def ApplicantDetail(request, applicant_user_email):
    auser = get_object_or_404(User, email__iexact=applicant_user_email)
    applicant, _ = Applicant.objects.get_or_create(author__email__iexact=applicant_user_email, defaults={'author_id': request.user.id})
    applicant_applications = Application.objects.filter(
        Q(applicant__author__email__iexact=applicant_user_email)
        ).exclude(deleted=True)

    return render(request,'icap/applicant.html', {'auser': auser, 'applicant': applicant, 'applicant_applications': applicant_applications,})

ApplicantFileFormSet = inlineformset_factory(Applicant, File, form=FileForm, can_delete=True)

def ApplicantUpdate(request):
    if request.user.is_authenticated:
        applicant, _ = Applicant.objects.get_or_create(author__email__iexact=request.user.email, defaults={'author_id': request.user.id})
        if request.method == "POST":
            form = ApplicantForm(request.POST, instance=applicant)
            fileformset = ApplicantFileFormSet(request.POST, request.FILES, instance=applicant)
            if form.is_valid():
                valid_applicant = form.save(commit=False)
                fileformset = ApplicantFileFormSet(request.POST, request.FILES, instance=applicant)
                if fileformset.is_valid():
                    valid_applicant.save()
                    form.save_m2m()
                    fset = fileformset.save(commit=False)
                    for f in fset:
                        f.author_id = request.user.id
                        f.save()
                    fileformset.save()
                    msg = 'Applicant <a class=\"alert-link\" href=\"/applicant/\">%s</a> updated.' % (valid_applicant.author.email)
                    messages.success(request, msg)
                    l = Logitem(author=request.user, status='S', message=msg, obj_model='Applicant', obj_id=valid_applicant.id, obj_in='', obj_out='',)
                    l.save()
                    return HttpResponseRedirect('/applicant/')

        else:
            form = ApplicantForm(instance=applicant)
            fileformset = ApplicantFileFormSet(instance=applicant)
    else:
        applicant = None
        form = None
        fileformset = None

    return render(request,'icap/applicant_update.html', {'applicant': applicant, 'form': form, 'fileformset': fileformset,})

