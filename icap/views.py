import os
import datetime
import uuid
import zipfile
from io import BytesIO
from django.shortcuts import get_object_or_404, render
from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Case, When, Q, F, Count, Value
#from django.db.models.functions import Replace
from django.db.models.functions import Lower
from django.contrib import messages
from django.contrib.auth.models import User
from django.forms.models import inlineformset_factory
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.core.mail import send_mail, send_mass_mail, mail_managers, EmailMessage
#from django.views.decorators.cache import cache_page
from django.conf import settings
from django.template.loader import render_to_string
from django.urls import reverse
from guardian.shortcuts import assign, get_users_with_perms, get_objects_for_user, remove_perm
from allauth.account.utils import *
from icap.models import *
from icap.forms import *
import re

fs = FileSystemStorage(location=settings.UFS)

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
            return HttpResponseRedirect(reverse('area_detail', args=[area_.slug]))
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
        no_applications = Applicant.objects.filter(area__slug__iexact=area_slug, application_applicant=None) 
        return render(request, 'icap/area_applicants.html', {'area': area_, 'area_applicants': area_applicants, 'no_applications': no_applications,})
    else:
        return HttpResponseRedirect(reverse('area_detail', args=[area_.slug]))

def AreaApplicantsReports(request, area_slug, switch):
    created = datetime.datetime.utcnow()
    created = created.strftime("%Y-%m-%dT%H:%M:%S")
    area_ = get_object_or_404(AreaUS, slug__iexact=area_slug)
    if request.user.has_perm('icap.manage_area', area_):
        exports = settings.STATIC_ROOT + 'exports/'
        if not os.path.exists(exports):
            os.makedirs(exports)
        area_applicants = Application.objects.filter(
            Q(position__team__area__slug__iexact=area_slug)
            ).exclude(deleted=True).select_related('applicant')
        if area_applicants:
            nominal = area_slug + '-' + created
            filename = nominal + str(uuid.uuid4())
            if switch == 'file-attachments':
                applicants = Application.objects.filter(
                    Q(position__team__area__slug__iexact=area_slug)
                    ).exclude(deleted=True).select_related('applicant').values('applicant_id')
                area_files = File.objects.filter(applicant__in=applicants).exclude(deleted=True)

                zip_filename = exports + filename + '.zip'
                zf = zipfile.ZipFile(zip_filename, "w")
                for f in area_files:
                    fn = settings.UFS + '/' + str(f.afile.name)
                    fdir, fname = os.path.split(fn)
                    zip_path = fn
                    zf.write(fn, fname)
                zf.close()
                fmsg = ' ' + str(len(area_files)) + ' files for ' + str(len(applicants)) + ' applicants zipped to <a class="alert-link" href="/s/exports/' + filename + '.zip">' + nominal + '.zip</a>.'
                ftxt = ' ' + str(len(area_files)) + ' files for ' + str(len(applicants)) + ' applicants zipped to https://' + settings.SITE_URL + '/s/exports/' + filename + '.zip.'
            else:
                fmsg = ''
                ftxt = ''

            msg = 'Area applicant reports emailed to <strong>' + request.user.email + '</strong> and written to <a class="alert-link" href="/s/exports/' + filename + '.csv">' + nominal + '.csv</a> and <a class="alert-link" href="/s/exports/' + filename + '.json">' + nominal + '.json</a>.' + fmsg
            txt = 'Area applicant reports emailed to ' + request.user.email + ' and written to https://' + settings.SITE_URL + '/s/exports/' + filename + '.csv and https://' + settings.SITE_URL + '/s/exports/' + filename + '.json.' + ftxt

            email = EmailMessage(
                'icap applicant report', txt, None, [request.user.email])
            context = { 'area_applicants': area_applicants, 'site': settings.SITE_URL }
            content = render_to_string('icap/area_applicants.csv', context)
            with open(exports + filename + '.csv', 'w') as static_file:
                static_file.write(content)
            email.attach_file(exports + filename + '.csv')
            content = render_to_string('icap/area_applicants.json', context)           
            with open(exports + filename + '.json', 'w') as static_file:
                static_file.write(content)
            email.attach_file(exports + filename + '.json')
            email.send()
            messages.info(request, msg)
            #l = Logitem(author=request.user, status='S', message=msg, obj_model='Fire', obj_id='', obj_in='', obj_out='',)
            #l.save()
        return HttpResponseRedirect(reverse('area_applicants', args=[area_.slug]))
    else:
        return HttpResponseRedirect(reverse('area_detail', args=[area_.slug]))

def TeamDetail(request, area_slug, team_slug):
    team = get_object_or_404(Team, Q(area__slug=area_slug), slug__iexact=team_slug)
    team_ics = Application.objects.filter(
        Q(position__team__slug__iexact=team_slug),
        Q(position__team__area__slug__iexact=area_slug),
        Q(position__code__in=['IC', 'ICT1', 'ICT2']),
        Q(status__in=['P','A',])
        ).exclude(deleted=True).select_related('applicant').values_list(Lower('author__email'), flat=True).distinct()
    if request.method == "POST":
        if "teamstatus" in request.POST:
            open_date = request.POST.get('open')
            close_date = request.POST.get('close')
            status = Team.objects.filter(Q(area__slug=area_slug, slug__iexact=team_slug)).update(author=request.user, open_date=open_date, close_date=close_date)
            msg = 'Open/close dates for <a class=\"alert-link\" href=\"/%s/%s/">%s &sect; %s</a> updated by %s. Position dates override team dates, team dates override area dates.' % (team.area.slug, team.slug, team.area, team, request.user.email)
            messages.success(request, msg)
            l = Logitem(author=request.user, status='S', message=msg, obj_model='Team', obj_id=team.id, obj_in='', obj_out='',)
            l.save()
            return HttpResponseRedirect(reverse('team_detail', args=[team.area.slug, team.slug]))

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
        ).exclude(deleted=True).select_related('applicant').values_list(Lower('author__email'), flat=True).distinct()
    if request.user.has_perm('icap.manage_area', team.area) or request.user.email.lower() in team_ics:
        team_applicants = Application.objects.filter(
            Q(position__team__slug__iexact=team_slug),
            Q(position__team__area__slug__iexact=area_slug)
            ).exclude(deleted=True).select_related('applicant')
        return render(request, 'icap/area_team_applicants.html', {'team': team, 'team_ics': team_ics, 'team_applicants': team_applicants,})
    else:
        return HttpResponseRedirect(reverse('team_detail', args=[team.area.slug, team.slug]))

def TeamApplicantsReports(request, area_slug, team_slug, switch):
    created = datetime.datetime.utcnow()
    created = created.strftime("%Y-%m-%dT%H:%M:%S")
    team = get_object_or_404(Team, Q(area__slug=area_slug), slug__iexact=team_slug)
    team_ics = Application.objects.filter(
        Q(position__team__slug__iexact=team_slug),
        Q(position__team__area__slug__iexact=area_slug),
        Q(position__code__in=['IC', 'ICT1', 'ICT2']),
        Q(status__in=['P','A',])
        ).exclude(deleted=True).select_related('applicant').values_list(Lower('author__email'), flat=True).distinct()
    if request.user.has_perm('icap.manage_area', team.area) or request.user.email.lower() in team_ics:
        exports = settings.STATIC_ROOT + '/exports/'
        if not os.path.exists(exports):
            os.makedirs(exports)
        team_applicants = Application.objects.filter(
            Q(position__team__slug__iexact=team_slug),
            Q(position__team__area__slug__iexact=area_slug)
            ).exclude(deleted=True).select_related('applicant')
        if team_applicants:
            #team_applicants.update(remarks=remarks.replace("\n", "<br/> ").replace("\r", "<br/> "))
            nominal = team_slug + '-' + created
            filename = nominal + str(uuid.uuid4())
            if switch == 'file-attachments':
                applicants = Application.objects.filter(
                    Q(position__team__slug__iexact=team_slug),
                    Q(position__team__area__slug__iexact=area_slug)
                    ).exclude(deleted=True).select_related('applicant').values('applicant_id')
                team_files = File.objects.filter(applicant__in=applicants).exclude(deleted=True)

                zip_filename = exports + filename + '.zip'
                zf = zipfile.ZipFile(zip_filename, "w")
                for f in team_files:
                    fn = settings.UFS + '/' + str(f.afile.name)
                    fdir, fname = os.path.split(fn)
                    zip_path = fn
                    zf.write(fn, fname)
                zf.close()
                fmsg = ' ' + str(len(team_files)) + ' files for ' + str(len(applicants)) + ' applicants zipped to <a class="alert-link" href="/s/exports/' + filename + '.zip">' + nominal + '.zip</a>.'
                ftxt = ' ' + str(len(team_files)) + ' files for ' + str(len(applicants)) + ' applicants zipped to https://' + settings.SITE_URL + '/s/exports/' + filename + '.zip.'
            else:
                fmsg = ''
                ftxt = ''

            msg = 'Team applicant reports emailed to <strong>' + request.user.email + '</strong> and written to <a class="alert-link" href="/s/exports/' + filename + '.csv">' + nominal + '.csv</a> and <a class="alert-link" href="/s/exports/' + filename + '.json">' + nominal + '.json</a>.' + fmsg
            txt = 'Team applicant reports emailed to ' + request.user.email + ' and written to https://' + settings.SITE_URL + '/s/exports/' + filename + '.csv and https://' + settings.SITE_URL + '/s/exports/' + filename + '.json.' + ftxt

            email = EmailMessage(
                'icap applicant report', txt, None, [request.user.email])
            context = { 'team_applicants': team_applicants }
            content = render_to_string('icap/team_applicants.csv', context)
            with open(exports + filename + '.csv', 'w') as static_file:
                static_file.write(content)
            email.attach_file(exports + filename + '.csv')
            content = render_to_string('icap/team_applicants.json', context)           
            with open(exports + filename + '.json', 'w') as static_file:
                static_file.write(content)
            email.attach_file(exports + filename + '.json')
            email.send()
            messages.info(request, msg)
            #l = Logitem(author=request.user, status='S', message=msg, obj_model='Fire', obj_id='', obj_in='', obj_out='',)
            #l.save()
        #msg = 'Unit and dispatch files written.'
        #messages.info(request, msg)
        return HttpResponseRedirect(reverse('team_applicants', args=[team.area.slug, team.slug]))
    else:
        return HttpResponseRedirect(reverse('area_detail', args=[area.slug]))

def ApplicationMessage(valid_application):
    a = 'applicant: ' + str(valid_application.applicant.firstname) + ' ' + str(valid_application.applicant.lastname) + ' ' + valid_application.applicant.author.email + '\n'
    a = a + 'category: ' + str(valid_application.applicant.category) + '\n'
    a = a + 'area: ' + str(valid_application.applicant.area) + '\n'
    a = a + 'host agency: ' + str(valid_application.applicant.host_agency) + '\n'
    a = a + 'city: ' + str(valid_application.applicant.city) + ', ' + str(valid_application.applicant.state) + '\n'
    a = a + 'dispatch: ' + str(valid_application.applicant.dispatch_office) + '\n'
    a = a + 'work: ' + str(valid_application.applicant.work) + '\n'
    a = a + 'home: ' + str(valid_application.applicant.home) + '\n'
    a = a + 'cell: ' + str(valid_application.applicant.cell) + '\n'
    a = a + 'iqcs/iqs: ' + str(valid_application.applicant.iqcs) + '\n'
    a = a + 'qualifications: ' + str(valid_application.applicant.qualifications) + '\n' + str(valid_application.qualifications) + '\n'
    a = a + 'remarks: ' + str(valid_application.applicant.remarks) + '\n' + valid_application.remarks + '\n'
    a = a + 'supervisor: ' + str(valid_application.applicant.supervisor_name) + ' ' + str(valid_application.applicant.supervisor_email) + '\n'
    a = a + 'training: ' + str(valid_application.applicant.training_name) + ' ' + str(valid_application.applicant.training_email) + '\n'
    a = a + 'admin: ' + str(valid_application.applicant.admin_name) + ' ' + str(valid_application.applicant.admin_email) + '\n'
    a = a + 'area: ' + str(valid_application.position.team.area.name) + '\n'
    a = a + 'team: ' + str(valid_application.position.team.name) + '\n'
    a = a + 'position: ' + str(valid_application.position.name) + '\n'
    a = a + 'consideration: ' + str(valid_application.get_consideration_display()) + '\n'
    return a

def TeamEmails(request, area_slug, team_slug):
    team = get_object_or_404(Team, Q(area__slug=area_slug), slug__iexact=team_slug)
    team_ics = Application.objects.filter(
        Q(position__team__slug__iexact=team_slug),
        Q(position__team__area__slug__iexact=area_slug),
        Q(position__code__in=['IC', 'ICT1', 'ICT2']),
        Q(status__in=['P','A',])
        ).exclude(deleted=True).select_related('applicant').values_list(Lower('author__email'), flat=True).distinct()
    team_applicants = Application.objects.filter(
        Q(position__team__slug__iexact=team_slug),
        Q(position__team__area__slug__iexact=area_slug)
        ).exclude(deleted=True).select_related('applicant')
    if request.user.has_perm('icap.manage_area', team.area) or request.user.email.lower() in team_ics:
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
                        if request.POST[e_applied_form] and team.area.e_applied is not None:
                            e_applied = datetime.datetime.now()
                            top = 'This email is to confirm your application to the positon below.\n\n'
                            a = ApplicationMessage(app)
                            bottom = '\n' + str(app.position.team.area.e_applied)
                            m = top + a + bottom
                            applied_mail = ('icap application confirmation', m, None, [app.applicant.author.email])
                            mails = mails + (applied_mail,)
                    else:
                        e_applied = app.e_applied
                    if e_supervisor_form in request.POST:
                        if request.POST[e_supervisor_form] and team.area.e_supervisor is not None:
                            e_supervisor = datetime.datetime.now()
                            r_supervisor = app.applicant.supervisor_email
                            a_supervisor = '' # date of approval
                            try:
                                supervisor, _ = User.objects.get_or_create(email__iexact=r_supervisor, defaults={'email': r_supervisor, 'username': r_supervisor, 'is_active': True})
                            except:
                                supervisor = User.objects.get(email__iexact=r_supervisor)
                                _ = False
                            if _:
                                send_email_confirmation(request, supervisor, True)
                                top = 'This email is to request supervisor\'s approval for the application below. You will receive an account confirmation in a separate email; please confirm your email and approve or disapprove this application.\n\n'
                            else:
                                top = 'This email is to request supervisor\'s approval for the application below.\n\n'
                            a = ApplicationMessage(app)
                            bottom = '\n' + str(app.position.team.area.e_supervisor)
                            m = top + a + bottom
                            supervisor_mail = ('icap approval request - supervisor', m, None, [r_supervisor])
                            mails = mails + (supervisor_mail,)
                    else:
                        e_supervisor = app.e_supervisor
                        r_supervisor = app.r_supervisor
                        a_supervisor = app.a_supervisor
                    if e_training_form in request.POST:
                        if request.POST[e_training_form] and team.area.e_training is not None:
                            e_training = datetime.datetime.now()
                            r_training = app.applicant.training_email
                            a_training = '' # date of approval
                            try:
                                training, _ = User.objects.get_or_create(email__iexact=r_training, defaults={'email': r_training, 'username': r_training, 'is_active': True})
                            except:
                                training = User.objects.get(email__iexact=r_training)
                                _ = False
                            if _:
                                send_email_confirmation(request, training, True)
                                top = 'This email is to request training coordinator\'s approval for the application below. You will receive an account confirmation in a separate email; please confirm your email and approve or disapprove this application.\n\n'
                            else:
                                top = 'This email is to request training coordinator\'s approval for the application below.\n\n'
                            a = ApplicationMessage(app)
                            bottom = '\n' + str(app.position.team.area.e_training)
                            m = top + a + bottom
                            training_mail = ('icap approval request - training', m, None, [r_training])
                            mails = mails + (training_mail,)
                    else:
                        e_training = app.e_training
                        r_training = app.r_training
                        a_training = app.a_training
                    if e_admin_form in request.POST:
                        if request.POST[e_admin_form] and team.area.e_admin is not None:
                            e_admin = datetime.datetime.now()
                            r_admin = app.applicant.admin_email
                            a_admin = '' # date of approval
                            try:
                                admin, _ = User.objects.get_or_create(email__iexact=r_admin, defaults={'email': r_admin, 'username': r_admin, 'is_active': True})
                            except:
                                admin = User.objects.get(email__iexact=r_admin)
                                _ = False
                            if _:
                                send_email_confirmation(request, admin, True)
                                top = 'This email is to request agency admin\'s approval for the application below. You will receive an account confirmation in a separate email; please confirm your email and approve or disapprove this application.\n\n'
                            else:
                                top = 'This email is to request agency admin\'s approval for the application below.\n\n'
                            a = ApplicationMessage(app)
                            bottom = '\n' + str(app.position.team.area.e_admin)
                            m = top + a + bottom
                            admin_mail = ('icap approval request - admin', m, None, [r_admin])
                            mails = mails + (admin_mail,)
                    else:
                        e_admin = app.e_admin
                        r_admin = app.r_admin
                        a_admin = app.a_admin
                    if e_selected_form in request.POST:
                        if request.POST[e_selected_form] and team.area.e_selected is not None:
                            e_selected = datetime.datetime.now()
                            # e_status
                            # e_status_author
                            # statused
                            top = 'This email is notify you of the selection status of the application below.\n\n'
                            a = ApplicationMessage(app)
                            a = a + 'selection status: ' + str(app.get_status_display()) + '\n'
                            bottom = '\n' + str(app.position.team.area.e_selected)
                            m = top + a + bottom
                            selected_mail = ('icap selection status notification', m, None, [app.applicant.author.email])
                            mails = mails + (selected_mail,)
                    else:
                        e_selected = app.e_selected
                    send_mass_mail(mails)
                    ok = Application.objects.filter(id=app.id).update(e_applied=e_applied, e_supervisor=e_supervisor, r_supervisor=r_supervisor, e_training=e_training, r_training=r_training, e_admin=e_admin, r_admin=r_admin, e_selected=e_selected)

            msg = 'Emails for <a class=\"alert-link\" href=\"/%s/%s/">%s &sect; %s</a> sent by %s.' % (team.area.slug, team.slug, team.area.name, team.name, request.user.email)
            messages.success(request, msg)
            l = Logitem(author=request.user, status='S', message=msg, obj_model='Application', obj_id='', obj_in='', obj_out='',)
            l.save()
            return HttpResponseRedirect(reverse('team_emails', args=[team.area.slug, team.slug]))
        return render(request, 'icap/area_team_emails.html', {'team': team, 'team_ics': team_ics, 'team_applicants': team_applicants,})
    else:
        return HttpResponseRedirect(reverse('team_detail', args=[team.area.slug, team.slug]))

def SetBlankApprovalEmails(): # for applications before approvals
    us = Application.objects.filter(r_supervisor__exact=None).select_related('applicant')
    for a in us:
        a.r_supervisor = a.applicant.supervisor_email
        a.save(update_fields=['r_supervisor'])
    ut = Application.objects.filter(r_training__exact=None).select_related('applicant')
    for a in ut:
        a.r_training = a.applicant.training_email
        a.save(update_fields=['r_training'])
    ua = Application.objects.filter(r_admin__exact=None).select_related('applicant')
    for a in ua:
        a.r_admin = a.applicant.admin_email
        a.save(update_fields=['r_admin'])
    m = 'Updated approval emails: S' + str(len(us)) + ' T' + str(len(ut)) + ' A' + str(len(ua))
    msg = '%s' % (m)
    l = Logitem(author=request.user, status='S', message=msg, obj_model='Application', obj_id='', obj_in='', obj_out='',)
    l.save()
    messages.success(request, msg)
    return HttpResponseRedirect(reverse('index'))

    us = Application.objects.filter(a_supervisor__exact=None)
    for a in us:
        a.approved_supervisor = None
        a.save(update_fields=['approved_supervisor'])

    ut = Application.objects.filter(a_training__exact=None)
    for a in ut:
        a.approved_training = None
        a.save(update_fields=['approved_training'])
    ua = Application.objects.filter(a_admin__exact=None)
    for a in ua:
        a.approved_admin = None
        a.save(update_fields=['approved_admin'])
    m = 'Updated approvals: S' + str(len(us)) + ' T' + str(len(ut)) + ' A' + str(len(ua))
    msg = '%s' % (m)
    l = Logitem(author=request.user, status='S', message=msg, obj_model='Application', obj_id='', obj_in='', obj_out='',)
    l.save()
    messages.success(request, msg)
    return HttpResponseRedirect(reverse('index'))

def TeamApprovals(request, area_slug, team_slug):
    team = get_object_or_404(Team, Q(area__slug=area_slug), slug__iexact=team_slug)
    team_ics = Application.objects.filter(
        Q(position__team__slug__iexact=team_slug),
        Q(position__team__area__slug__iexact=area_slug),
        Q(position__code__in=['IC', 'ICT1', 'ICT2']),
        Q(status__in=['P','A',])
        ).exclude(deleted=True).select_related('applicant').values_list(Lower('author__email'), flat=True).distinct()
    if request.user.has_perm('icap.manage_area', team.area) or request.user.email.lower() in team_ics:
        applications = Application.objects.filter(
            Q(position__team__slug__iexact=team_slug),
            Q(position__team__area__slug__iexact=area_slug)
            ).exclude(deleted=True).select_related('applicant')
    else:
        msg = 'Login to set approvals.'
        messages.success(request, msg)
        return HttpResponseRedirect(reverse('index'))
    if request.method == "POST":
        if "approvals" in request.POST:
            for app in applications:
                a_supervisor_form = 'a_supervisor_' + str(app.id)
                a_training_form = 'a_training_' + str(app.id)
                a_admin_form = 'a_admin_' + str(app.id)
                if a_supervisor_form in request.POST:
                    if request.POST[a_supervisor_form] and app.r_supervisor.lower() == request.user.email.lower():
                        a_supervisor = datetime.datetime.now()
                        approved_supervisor = True # request.POST[a_supervisor_form]
                elif app.r_supervisor.lower() == request.user.email.lower():
                    a_supervisor = datetime.datetime.now()
                    approved_supervisor = False # request.POST[a_supervisor_form]
                else:
                    a_supervisor = app.a_supervisor
                    approved_supervisor = app.approved_supervisor
                if a_training_form in request.POST:
                    if request.POST[a_training_form] and app.r_training.lower() == request.user.email.lower():
                        a_training = datetime.datetime.now()
                        approved_training = True # request.POST[a_training_form]
                elif app.r_training.lower() == request.user.email.lower():
                    a_training = datetime.datetime.now()
                    approved_training = False # request.POST[a_training_form]
                else:
                    a_training = app.a_training
                    approved_training = app.approved_training
                if a_admin_form in request.POST:
                    if request.POST[a_admin_form] and app.r_admin.lower() == request.user.email.lower():
                        a_admin = datetime.datetime.now()
                        approved_admin = True # request.POST[a_training_form]
                elif app.r_admin.lower() == request.user.email.lower():
                    a_admin = datetime.datetime.now()
                    approved_admin = False # request.POST[a_training_form]
                else:
                    a_admin = app.a_admin
                    approved_admin = app.approved_admin
                ok = Application.objects.filter(id=app.id).update(a_supervisor=a_supervisor, approved_supervisor=approved_supervisor, a_training=a_training, approved_training=approved_training, a_admin=a_admin, approved_admin=approved_admin,)

        msg = 'Application approvals set by %s.' % (request.user.email)
        messages.success(request, msg)
        l = Logitem(author=request.user, status='S', message=msg, obj_model='Application', obj_id='', obj_in='', obj_out='',)
        l.save()
        return HttpResponseRedirect(reverse('team_approvals', args=[team.area.slug, team.slug]))

    return render(request, 'icap/area_team_approvals.html', {'team': team, 'team_ics': team_ics, 'applications': applications,})


def PositionDetail(request, area_slug, team_slug, position_slug):
    position = get_object_or_404(Position, Q(team__area__slug=area_slug), Q(team__slug=team_slug), slug__iexact=position_slug)
    team_ics = Application.objects.filter(
        Q(position__team__slug__iexact=team_slug),
        Q(position__team__area__slug__iexact=area_slug),
        Q(position__code__in=['IC', 'ICT1', 'ICT2']),
        Q(status__in=['P','A',])
        ).exclude(deleted=True).select_related('applicant').values_list(Lower('author__email'), flat=True).distinct()
    position_applications = Application.objects.filter(
        Q(position__slug__iexact=position_slug),
        Q(position__team__slug__iexact=team_slug) | Q(position__team__slug__endswith='applicant-pool'),
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
                    if app.position != position and app.position.team.slug.endswith('applicant-pool'):
                        set_status = ApplicationStatus.objects.create(author=request.user, application=app, status='W', effective=app_statused)
                        ok = Application.objects.filter(id=app.id).update(status_author=request.user, status='W', statused=app_statused)
                        app.pk = None
                        app.position = position
                        app.status = app_status
                        app.save()
                        set_status = ApplicationStatus.objects.create(author=request.user, application=app, status=app_status, effective=app_statused)
                    else:
                        set_status = ApplicationStatus.objects.create(author=request.user, application=app, status=app_status, effective=app_statused)
                        ok = Application.objects.filter(id=app.id).update(status_author=request.user, status=app_status, statused=app_statused)
                    msg = 'Application for %s to <a class=\"alert-link\" href=\"/%s/%s/%s/\">%s &sect; %s &sect; %s</a> updated by %s.' % (app.applicant.author.email, position.team.area.slug, position.team.slug, position.slug, position.team.area, position.team, position.name, request.user.email)
                    messages.success(request, msg)

            msg = '%s applications to <a class=\"alert-link\" href=\"/%s/%s/%s/\">%s &sect; %s &sect; %s</a> updated by %s.' % (position_applications.count(), position.team.area.slug, position.team.slug, position.slug, position.team.area, position.team, position.name, request.user.email)
            messages.success(request, msg)
            l = Logitem(author=request.user, status='S', message=msg, obj_model='ApplicationStatus', obj_id='', obj_in='', obj_out='',)
            l.save()
            return HttpResponseRedirect(reverse('position_detail', args=[position.team.area.slug, position.team.slug, position.slug]))
        else:
            for app in position_applications:
                app_button = 'app_' + str(app.id)
                if app_button in request.POST:
                    app_form = 'application_status_' + str(app.id)
                    if app_form in request.POST:
                        app_statused = datetime.datetime.now()
                        app_status = request.POST.get(app_form, '')
                        if app.position != position and app.position.team.slug.endswith('applicant-pool'):
                            set_status = ApplicationStatus.objects.create(author=request.user, application=app, status='W', effective=app_statused)
                            ok = Application.objects.filter(id=app.id).update(status_author=request.user, status='W', statused=app_statused)
                            app.pk = None
                            app.position = position
                            app.status = app_status
                            app.save()
                            set_status = ApplicationStatus.objects.create(author=request.user, application=app, status=app_status, effective=app_statused)
                        else:
                            set_status = ApplicationStatus.objects.create(author=request.user, application=app, status=app_status, effective=app_statused)
                            ok = Application.objects.filter(id=app.id).update(status_author=request.user, status=app_status, statused=app_statused)
                        msg = 'Application for %s to <a class=\"alert-link\" href=\"/%s/%s/%s/\">%s &sect; %s &sect; %s</a> updated by %s.' % (app.applicant.author.email, position.team.area.slug, position.team.slug, position.slug, position.team.area, position.team, position.name, request.user.email)
                        messages.success(request, msg)
                        l = Logitem(author=request.user, status='S', message=msg, obj_model='ApplicationStatus', obj_id='', obj_in='', obj_out='',)
                        l.save()
                        return HttpResponseRedirect(reverse('position_detail', args=[position.team.area.slug, position.team.slug, position.slug]))

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
            return HttpResponseRedirect(reverse('position_detail', args=[position.team.area.slug, position.team.slug, position.slug]))

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
            if position.team.area.e_applied and valid_application.applicant.author.email:
                top = 'This email is to confirm your application to the positon below.\n\n'
                a = 'applicant: ' + str(valid_application.applicant.firstname) + ' ' + str(valid_application.applicant.lastname) + ' ' + valid_application.applicant.author.email + '\n'
                a = a + 'category: ' + str(valid_application.applicant.category) + '\n'
                a = a + 'area: ' + str(valid_application.applicant.area) + '\n'
                a = a + 'host agency: ' + str(valid_application.applicant.host_agency) + '\n'
                a = a + 'city: ' + str(valid_application.applicant.city) + ', ' + str(valid_application.applicant.state) + '\n'
                a = a + 'dispatch: ' + str(valid_application.applicant.dispatch_office) + '\n'
                a = a + 'work: ' + str(valid_application.applicant.work) + '\n'
                a = a + 'home: ' + str(valid_application.applicant.home) + '\n'
                a = a + 'cell: ' + str(valid_application.applicant.cell) + '\n'
                a = a + 'iqcs/iqs: ' + str(valid_application.applicant.iqcs) + '\n'
                a = a + 'qualifications: ' + str(valid_application.applicant.qualifications) + '\n' + str(valid_application.qualifications) + '\n'
                a = a + 'remarks: ' + str(valid_application.applicant.remarks) + '\n' + valid_application.remarks + '\n'
                a = a + 'supervisor: ' + str(valid_application.applicant.supervisor_name) + ' ' + str(valid_application.applicant.supervisor_email) + '\n'
                a = a + 'training: ' + str(valid_application.applicant.training_name) + ' ' + str(valid_application.applicant.training_email) + '\n'
                a = a + 'admin: ' + str(valid_application.applicant.admin_name) + ' ' + str(valid_application.applicant.admin_email) + '\n'
                a = a + 'area: ' + str(valid_application.position.team.area.name) + '\n'
                a = a + 'team: ' + str(valid_application.position.team.name) + '\n'
                a = a + 'position: ' + str(valid_application.position.name) + '\n'
                a = a + 'consideration: ' + str(valid_application.get_consideration_display()) + '\n'
                bottom = '\n' + str(position.team.area.e_applied)
                m = top + a + bottom
                applied_mail = EmailMessage('icap application confirmation', m, None, [valid_application.applicant.author.email])
                applied_mail.send()
                valid_application.e_applied = datetime.datetime.now()
                valid_application.save()
            msg = 'Application to <a class=\"alert-link\" href=\"/%s/%s/%s/\">%s &sect; %s &sect; %s</a> for <a class=\"alert-link\" href=\"/applicant/%s/\">%s</a> updated.' % (position.team.area.slug, position.team.slug, position.slug, position.team.area, position.team, position.name, valid_application.applicant.author.email, valid_application.applicant.author.email)
            messages.success(request, msg)
            l = Logitem(author=request.user, status='S', message=msg, obj_model='Application', obj_id=valid_application.id, obj_in='', obj_out='',)
            l.save()
            return HttpResponseRedirect(reverse('applicant_detail', args=[applicant.author.email]))
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
    applicant_teams = applicant_applications.order_by().values_list('position__team', flat=True).distinct()
    applicant_ics = Application.objects.filter(
        Q(position__team__in=applicant_teams),
        #Q(position__team__area__slug__iexact=area_slug),
        Q(position__code__in=['IC', 'ICT1', 'ICT2']),
        Q(status__in=['P','A',])
        ).exclude(deleted=True).select_related('applicant').values_list(Lower('author__email'), flat=True).distinct()
    return render(request,'icap/applicant.html', {'auser': auser, 'applicant': applicant, 'applicant_applications': applicant_applications, 'applicant_teams': applicant_teams, 'applicant_ics': applicant_ics})

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
                    #return HttpResponseRedirect(reverse('applicant_update'))
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

def Approvals(request):
    if request.user.is_authenticated:
        applications = Application.objects.filter(Q(r_supervisor__iexact=request.user.email)|Q(r_training__iexact=request.user.email)|Q(r_admin__iexact=request.user.email))
    else:
        msg = 'Login to set approvals.'
        messages.success(request, msg)
        return HttpResponseRedirect(reverse('index'))
    if request.method == "POST":
        if "approvals" in request.POST:
            for app in applications:
                a_supervisor_form = 'a_supervisor_' + str(app.id)
                a_training_form = 'a_training_' + str(app.id)
                a_admin_form = 'a_admin_' + str(app.id)
                if a_supervisor_form in request.POST:
                    if request.POST[a_supervisor_form] and app.r_supervisor.lower() == request.user.email.lower():
                        a_supervisor = datetime.datetime.now()
                        approved_supervisor = True # request.POST[a_supervisor_form]
                elif app.r_supervisor.lower() == request.user.email.lower():
                    a_supervisor = datetime.datetime.now()
                    approved_supervisor = False # request.POST[a_supervisor_form]
                else:
                    a_supervisor = app.a_supervisor
                    approved_supervisor = app.approved_supervisor
                if a_training_form in request.POST:
                    if request.POST[a_training_form] and app.r_training.lower() == request.user.email.lower():
                        a_training = datetime.datetime.now()
                        approved_training = True # request.POST[a_training_form]
                elif app.r_training.lower() == request.user.email.lower():
                    a_training = datetime.datetime.now()
                    approved_training = False # request.POST[a_training_form]
                else:
                    a_training = app.a_training
                    approved_training = app.approved_training
                if a_admin_form in request.POST:
                    if request.POST[a_admin_form] and app.r_admin.lower() == request.user.email.lower():
                        a_admin = datetime.datetime.now()
                        approved_admin = True # request.POST[a_training_form]
                elif app.r_admin.lower() == request.user.email.lower():
                    a_admin = datetime.datetime.now()
                    approved_admin = False # request.POST[a_training_form]
                else:
                    a_admin = app.a_admin
                    approved_admin = app.approved_admin
                ok = Application.objects.filter(id=app.id).update(a_supervisor=a_supervisor, approved_supervisor=approved_supervisor, a_training=a_training, approved_training=approved_training, a_admin=a_admin, approved_admin=approved_admin,)

        msg = 'Application approvals set by %s.' % (request.user.email)
        messages.success(request, msg)
        l = Logitem(author=request.user, status='S', message=msg, obj_model='Application', obj_id='', obj_in='', obj_out='',)
        l.save()
        return HttpResponseRedirect(reverse('approvals'))

    return render(request, 'icap/approvals.html', {'applications': applications,})

def Units(request):
    if request.user.is_superuser:
        path = settings.STATIC_ROOT
        os.makedirs(path, exist_ok=True)
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
        msg = 'Unit and dispatch files written.'
        messages.info(request, msg)
        return HttpResponseRedirect('/')
    else:
        return HttpResponseRedirect('/')
