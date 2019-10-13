import os
import datetime
from django.shortcuts import get_object_or_404, render
from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Case, When, Q, F, Count, Value
#from django.db.models.functions import Replace
from django.contrib import messages
from django.contrib.auth.models import User
from django.forms.models import inlineformset_factory
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.core.mail import send_mail, send_mass_mail, mail_managers
#from django.views.decorators.cache import cache_page
from django.conf import settings
from django.template.loader import render_to_string
from guardian.shortcuts import assign, get_users_with_perms, get_objects_for_user, remove_perm
from icap.models import *
from icap.forms import *

def Feedback(request):
    when = datetime.datetime.now()
    if request.method == 'POST':
        form = FeedbackForm(request.POST)
        if form.is_valid():
            fn = form.cleaned_data['fullname']
            em = form.cleaned_data['email']
            fm = form.cleaned_data['feedback']
            mailfrom = 'feedback@' + request.get_host()
            mtxt = "Feedback from " + settings.SITE_URL + ". \r\n" + fn +"\r\n" + em +"\r\n" + fm +"\r\n"
            mhtm = "Feedback from user " + settings.SITE_URL + ". <br/><br/>" + fn + "<br/>" + em + "<br/>" + fm + "<br/>"
            msubj = "Feedback from " + settings.SITE_URL
            msg = mail_managers(msubj, mtxt, html_message=mhtm)
            m = 'Feedback sent. Thank your for your comment or complaint.'
            messages.success(request, m)
            return HttpResponseRedirect('/')
    else:
        form = FeedbackForm()

    return render(request, 'icap/feedback.html', {'when': when, 'form': form, })

def update_user_login(sender, user, **kwargs):
    msg = 'User %s login successful.' % (user.email)
    l = Logitem(author=user, status='S', message=msg, obj_model='Session', obj_id='', obj_in='', obj_out='',)
    l.save()
    if not user.has_perm('icap.add_applicant'):
        assign('icap.add_applicant', user)
    #user.userlogin_set.create(timestamp=timezone.now())
    #user.save()

user_logged_in.connect(update_user_login)

def Index(request):
    areas = AreaUS.objects.exclude(deleted=True)
    if request.user.is_authenticated:
        applicant = Applicant.objects.filter(author__email__iexact=request.user.email).count()
        applicant_applications = Application.objects.filter(
            Q(applicant__author__email__iexact=request.user.email)
            ).exclude(deleted=True).count()
    else:
        applicant = 0
        applicant_applications = 0
    return render(request, 'index.html', {'areas': areas, 'applicant': applicant, 'applicant_applications': applicant_applications})

def AreaDetail(request, area_slug):
    area_ = get_object_or_404(AreaUS, slug__iexact=area_slug)
    if request.method == "POST":
        if "areastatus" in request.POST:
            open_date = request.POST.get('open')
            close_date = request.POST.get('close')
            status = AreaUS.objects.filter(slug__iexact=area_slug).update(author=request.user, open_date=open_date, close_date=close_date)
            msg = 'Open/close dates for <a class=\"alert-link\" href=\"/%s/">%s</a> updated by %s. Position dates override team dates, team dates override area dates.' % (area_.slug, area_, request.user.email)
            messages.success(request, msg)
            l = Logitem(author=request.user, status='S', message=msg, obj_model='Area', obj_id=area_.id, obj_in='', obj_out='',)
            l.save()
            return HttpResponseRedirect('/%s/' % (area_.slug))
    area_teams = Team.objects.filter(
        Q(area__slug__iexact=area_slug)
        ).exclude(deleted=True)
    return render(request, 'icap/area.html', {'area': area_, 'area_teams': area_teams,})

def AreaApplicants(request, area_slug):
    area_ = get_object_or_404(AreaUS, slug__iexact=area_slug)
    if request.user.has_perm('icap.manage_area', area_):
        area_applicants = Application.objects.filter(
            Q(position__team__area__slug__iexact=area_slug)
            ).exclude(deleted=True).select_related('applicant')
        return render(request, 'icap/area_applicants.html', {'area': area_, 'area_applicants': area_applicants,})
    else:
        return HttpResponseRedirect('/%s/' % (area_.slug))

def AreaEmails(request, area_slug): # not finished
    area_ = get_object_or_404(AreaUS, slug__iexact=area_slug)
    if request.user.has_perm('icap.manage_area', area_):
        if request.method == "POST":
            return HttpResponseRedirect('/%s/' % (area_.slug))
        area_applicants = Application.objects.filter(
            Q(position__team__area__slug__iexact=area_slug)
            ).exclude(deleted=True).select_related('applicant')
        msg = 'Emails for <a class=\"alert-link\" href=\"/%s/">%s</a> updated by %s. Select junk mail to send in the table below.' % (area_.slug, area_.name, request.user.email)
        messages.info(request, msg)
        l = Logitem(author=request.user, status='I', message=msg, obj_model='Area', obj_id=area_.id, obj_in='', obj_out='',)
        l.save()

        return render(request, 'icap/area_emails.html', {'area': area_, 'area_applicants': area_applicants,})
    else:
        return HttpResponseRedirect('/%s/' % (area_.slug))

def TeamDetail(request, area_slug, team_slug):
    team = get_object_or_404(Team, Q(area__slug=area_slug), slug__iexact=team_slug)
    team_ics = Application.objects.filter(
        Q(position__team__slug__iexact=team_slug),
        Q(position__team__area__slug__iexact=area_slug),
        Q(position__code__in=['IC', 'ICT1', 'ICT2']),
        Q(status__in=['P','A',])
        ).exclude(deleted=True).select_related('applicant').values_list('author__email', flat=True).distinct()
    if request.method == "POST":
        if "teamstatus" in request.POST:
            open_date = request.POST.get('open')
            close_date = request.POST.get('close')
            status = Team.objects.filter(Q(area__slug=area_slug, slug__iexact=team_slug)).update(author=request.user, open_date=open_date, close_date=close_date)
            msg = 'Open/close dates for <a class=\"alert-link\" href=\"/%s/%s/">%s &sect; %s</a> updated by %s. Position dates override team dates, team dates override area dates.' % (team.area.slug, team.slug, team.area, team, request.user.email)
            messages.success(request, msg)
            l = Logitem(author=request.user, status='S', message=msg, obj_model='Team', obj_id=team.id, obj_in='', obj_out='',)
            l.save()
            return HttpResponseRedirect('/%s/%s/' % (team.area.slug, team.slug))
    team_positions = Position.objects.filter(
        Q(team__slug__iexact=team_slug),
        Q(team__area__slug__iexact=area_slug)
        ).exclude(deleted=True).annotate(num_apps=Count('application_position'))
    selects = Position.objects.filter(
        Q(team__slug__iexact=team_slug),
        Q(team__area__slug__iexact=area_slug)
        ).exclude(deleted=True).annotate(primary=Case(When(application_position__status="P", then='application_position__applicant__author__email')), trainee=Case(When(application_position__status="T", then='application_position__applicant__author__email'))).order_by('name', 'application_position__status')
    temp1dict = {}
    temp2dict = {}
    hold = None
    for position in selects:
        if position.id != hold:
            temp1dict[position] = []
            temp2dict[position] = []
        if position.primary is not None:
            temp1dict[position].append(position.primary)
        if position.trainee is not None:
            temp2dict[position].append(position.trainee)
        hold = position.id
    for position in team_positions:
        position.primary = temp1dict.get(position, 0)
        position.trainee = temp2dict.get(position, 0)

    return render(request, 'icap/area_team.html', {'team': team, 'team_ics': team_ics, 'team_positions': team_positions})

def TeamApplicants(request, area_slug, team_slug):
    team = get_object_or_404(Team, Q(area__slug=area_slug), slug__iexact=team_slug)
    team_ics = Application.objects.filter(
        Q(position__team__slug__iexact=team_slug),
        Q(position__team__area__slug__iexact=area_slug),
        Q(position__code__in=['IC', 'ICT1', 'ICT2']),
        Q(status__in=['P','A',])
        ).exclude(deleted=True).select_related('applicant').values_list('author__email', flat=True).distinct()
    if request.user.has_perm('icap.manage_area', team.area) or request.user.email in team_ics:
        team_applicants = Application.objects.filter(
            Q(position__team__slug__iexact=team_slug),
            Q(position__team__area__slug__iexact=area_slug)
            ).exclude(deleted=True).select_related('applicant')
        return render(request, 'icap/area_team_applicants.html', {'team': team, 'team_ics': team_ics, 'team_applicants': team_applicants,})
    else:
        return HttpResponseRedirect('/%s/%s/' % (team.area.slug, team.slug))

def TeamEmails(request, area_slug, team_slug): # not finished
    team = get_object_or_404(Team, Q(area__slug=area_slug), slug__iexact=team_slug)
    team_ics = Application.objects.filter(
        Q(position__team__slug__iexact=team_slug),
        Q(position__team__area__slug__iexact=area_slug),
        Q(position__code__in=['IC', 'ICT1', 'ICT2']),
        Q(status__in=['P','A',])
        ).exclude(deleted=True).select_related('applicant').values_list('author__email', flat=True).distinct()
    team_applicants = Application.objects.filter(
        Q(position__team__slug__iexact=team_slug),
        Q(position__team__area__slug__iexact=area_slug)
        ).exclude(deleted=True).select_related('applicant')
    if request.user.has_perm('icap.manage_area', team.area) or request.user.email in team_ics:
        if request.method == "POST":
            if "emails" in request.POST:
                for app in team_applicants:
                    e_applied_form = 'e_applied_' + str(app.id)
                    e_supervisor_form = 'e_supervisor_' + str(app.id)
                    e_training_form = 'e_training_' + str(app.id)
                    e_admin_form = 'e_admin_' + str(app.id)
                    e_selected_form = 'e_selected_' + str(app.id)
                    mails = ()
                    if e_applied_form in request.POST:
                        if request.POST[e_applied_form]:
                            e_applied = datetime.datetime.now()
                            if team.area.e_applied is not None:
                                m = team.area.e_applied
                            else:
                                m = ''
                            applied_mail = ('icap application confirmation', m, None, [app.applicant.author.email])
                            mails = mails + (applied_mail,)
                    else:
                        e_applied = app.e_applied
                    if e_supervisor_form in request.POST:
                        if request.POST[e_supervisor_form]:
                            e_supervisor = datetime.datetime.now()
                            r_supervisor = app.applicant.supervisor_email
                            a_supervisor = '' # date of approval
                            if team.area.e_supervisor is not None:
                                m = team.area.e_supervisor
                            else:
                                m = ''
                            supervisor_mail = ('icap approval request - supervisor', m, None, [r_supervisor])
                            mails = mails + (supervisor_mail,)
                    else:
                        e_supervisor = app.e_supervisor
                        r_supervisor = app.r_supervisor
                    if e_training_form in request.POST:
                        if request.POST[e_training_form]:
                            e_training = datetime.datetime.now()
                            r_training = app.applicant.training_email
                            a_training = '' # date of approval
                            if team.area.e_training is not None:
                                m = team.area.e_training
                            else:
                                m = ''
                            training_mail = ('icap approval request - training', m, None, [r_training])
                            mails = mails + (training_mail,)
                    else:
                        e_training = app.e_training
                        r_training = app.r_training
                    if e_admin_form in request.POST:
                        if request.POST[e_admin_form]:
                            e_admin = datetime.datetime.now()
                            r_admin = app.applicant.admin_email
                            a_admin = '' # date of approval
                            if team.area.e_admin is not None:
                                m = team.area.e_admin
                            else:
                                m = ''
                            admin_mail = ('icap approval request - agency', m, None, [r_admin])
                            mails = mails + (admin_mail,)
                    else:
                        e_admin = app.e_admin
                        r_admin = app.r_admin
                    if e_selected_form in request.POST:
                        if request.POST[e_selected_form]:
                            e_selected = datetime.datetime.now()
                            # e_status
                            # e_status_author
                            # statused
                            if team.area.e_selected is not None:
                                m = team.area.e_selected
                            else:
                                m = ''
                            selected_mail = ('icap selection notification', m, None, [app.applicant.author.email])
                            mails = mails + (selected_mail,)
                    else:
                        e_selected = app.e_selected
                    send_mass_mail(mails)
                    ok = Application.objects.filter(id=app.id).update(e_applied=e_applied, e_supervisor=e_supervisor, r_supervisor=r_supervisor, e_training=e_training, r_training=r_training, e_admin=e_admin, r_admin=r_admin, e_selected=e_selected)

            msg = 'Emails for <a class=\"alert-link\" href=\"/%s/%s/">%s &sect; %s</a> sent by %s.' % (team.area.slug, team.slug, team.area.name, team.name, request.user.email)
            messages.success(request, msg)
            l = Logitem(author=request.user, status='S', message=msg, obj_model='Application', obj_id='', obj_in='', obj_out='',)
            l.save()
            return HttpResponseRedirect('/%s/%s/emails/' % (team.area.slug, team.slug))
        return render(request, 'icap/area_team_emails.html', {'team': team, 'team_ics': team_ics, 'team_applicants': team_applicants,})
    else:
        return HttpResponseRedirect('/%s/%s/' % (team.area.slug, team.slug))

def PositionDetail(request, area_slug, team_slug, position_slug):
    position = get_object_or_404(Position, Q(team__area__slug=area_slug), Q(team__slug=team_slug), slug__iexact=position_slug)
    team_ics = Application.objects.filter(
        Q(position__team__slug__iexact=team_slug),
        Q(position__team__area__slug__iexact=area_slug),
        Q(position__code__in=['IC', 'ICT1', 'ICT2']),
        Q(status__in=['P','A',])
        ).exclude(deleted=True).select_related('applicant').values_list('author__email', flat=True).distinct()
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
                    app_statused = datetime.datetime.now()
                    app_status = request.POST.get(app_form, '')
                    set_status = ApplicationStatus.objects.create(author=request.user, application=app, status=app_status, effective=app_statused)
                    ok = Application.objects.filter(id=app.id).update(status_author=request.user, status=app_status, statused=app_statused)
                    msg = 'Application for %s to <a class=\"alert-link\" href=\"/%s/%s/%s/\">%s &sect; %s &sect; %s</a> updated by %s.' % (app.applicant.author.email, position.team.area.slug, position.team.slug, position.slug, position.team.area, position.team, position.name, request.user.email)
                    messages.success(request, msg)

            msg = '%s applications to <a class=\"alert-link\" href=\"/%s/%s/%s/\">%s &sect; %s &sect; %s</a> updated by %s.' % (position_applications.count(), position.team.area.slug, position.team.slug, position.slug, position.team.area, position.team, position.name, request.user.email)
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
                        app_statused = datetime.datetime.now()
                        app_status = request.POST.get(app_form, '')
                        set_status = ApplicationStatus.objects.create(author=request.user, application=app, status=app_status, effective=app_statused)
                        ok = Application.objects.filter(id=app.id).update(status_author=request.user, status=app_status, statused=app_statused)
                        msg = 'Application for %s to <a class=\"alert-link\" href=\"/%s/%s/%s/\">%s &sect; %s &sect; %s</a> updated by %s.' % (app.applicant.author.email, position.team.area.slug, position.team.slug, position.slug, position.team.area, position.team, position.name, request.user.email)
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
            msg = 'Open/close dates for <a class=\"alert-link\" href=\"/%s/%s/%s/\">%s &sect; %s &sect; %s</a> updated by %s. Position dates override team dates, team dates override area dates.' % (position.team.area.slug, position.team.slug, position.slug, position.team.area, position.team, position.name, request.user.email)
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
            msg = 'Application to <a class=\"alert-link\" href=\"/%s/%s/%s/\">%s &sect; %s &sect; %s</a> for <a class=\"alert-link\" href=\"/applicant/%s/\">%s</a> updated.' % (position.team.area.slug, position.team.slug, position.slug, position.team.area, position.team, position.name, valid_application.applicant.author.email, valid_application.applicant.author.email)
            messages.success(request, msg)
            l = Logitem(author=request.user, status='S', message=msg, obj_model='Applicant', obj_id=valid_application.id, obj_in='', obj_out='',)
            l.save()
            return HttpResponseRedirect('/applicant/%s/' % (applicant.author.email))
    else:
        if position_application:
            form = ApplicationForm(instance=position_application)
        else:
            form = ApplicationForm()

    return render(request, 'icap/area_team_position.html', {'position': position, 'team_ics': team_ics, 'position_applications': position_applications, 'applicant': applicant, 'position_application': position_application, 'form': form,})

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
                    #return HttpResponseRedirect('/applicant/')
        else:
            form = ApplicantForm(instance=applicant)
            fileformset = ApplicantFileFormSet(instance=applicant)
            msg = 'Fill out the form below <strong>COMPLETELY</strong>. This message will be replaced with a success alert when your applicant form has been submitted successsfully.'
            messages.info(request, msg)
    else:
        applicant = None
        form = None
        fileformset = None

    return render(request, 'icap/applicant_update.html', {'applicant': applicant, 'form': form, 'fileformset': fileformset,})

def Units(request):
    if request.user.is_superuser:
        path = '/home/ordvac/webapps/icap_ordvac_s/'
        os.makedirs(path, exist_ok=True)
        #units = Unit.objects.filter(deleted__isnull=False)
        #chars = ['\'', '-', '&']
        #query = Q()
        #for char in chars:
        #    query = query | Q(name__icontains=char)
        #Unit.objects.filter(query).update(
        #    string_field=Replace('name', Value('\''), Value(''))
        #)
        #ok = Unit.objects.filter(query).update(name=self.name.replace('\'','').replace('-',' ').replace('&','and'))
        
        units = Unit.objects.exclude(deleted__isnull=False)
        if units:
            context = { 'units': units }
            content = render_to_string('icap/unit.csv', context)           
            with open(path + 'unit.csv', 'w') as static_file:
                static_file.write(content)
            content = render_to_string('icap/unit.json', context)           
            with open(path + 'unit.json', 'w') as static_file:
                static_file.write(content)
                msg = 'Unit file written to <a href="/s/unit.csv">/s/unit.csv</a> and <a href="/s/unit.json">/s/unit.json</a>.'
            messages.info(request, msg)
            #l = Logitem(author=request.user, status='S', message=msg, obj_model='Fire', obj_id='', obj_in='', obj_out='',)
            #l.save()
        dispatch = Unit.objects.filter(wildlandrole__iexact='Dispatch/Coordination Center').exclude(deleted__isnull=False)#.annotate(clean=unit.replace('\'','').replace('-',' ').replace('&','and'))
        if dispatch:
            context = { 'units': dispatch }
            content = render_to_string('icap/dispatch.csv', context)           
            with open(path + 'dispatch.csv', 'w') as static_file:
                static_file.write(content)
            content = render_to_string('icap/dispatch.json', context)           
            with open(path + 'dispatch.json', 'w') as static_file:
                static_file.write(content)
                msg = 'Dispatch file written to <a href="/s/dispatch.csv">/s/dispatch.csv</a> and <a href="/s/dispatch.json">/s/dispatch.json</a>.'
            messages.info(request, msg)
            #l = Logitem(author=request.user, status='S', message=msg, obj_model='Fire', obj_id='', obj_in='', obj_out='',)
            #l.save()
        #msg = 'Unit and dispatch files written.'
        #messages.info(request, msg)
        return HttpResponseRedirect('/')
    else:
        return HttpResponseRedirect('/')
