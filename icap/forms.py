import datetime

from django import forms
from django.http import *
from django.forms.formsets import formset_factory
from django.utils.timezone import utc
from django.forms.widgets import ClearableFileInput
from taggit.forms import TagField, TagWidget

from icap.models import *

timenow = datetime.datetime.utcnow().replace(tzinfo=utc)

class FeedbackForm(forms.Form):
    fullname = forms.CharField(required=False,)
    email = forms.CharField(label='email', max_length=80, widget=forms.TextInput(attrs={'class':'form-control form-control-sm', 'pattern': '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-z]{2,4}$', 'placeholder':'your_email@example.com'}))
    feedback = forms.CharField(required=False, widget=forms.Textarea(attrs={'class':'span9', 'placeholder':'Type a message here.', 'rows': 5}))

class FileForm(forms.ModelForm):
    afile = forms.FileField(label='file upload', required=False, widget=ClearableFileInput(attrs={'class':'low',}))
    tags = TagField(label='tags', required=False, widget=TagWidget(attrs={'class':'form-control form-control-sm', }))

    class Meta:
        model = File
        exclude = ['created', 'modified', 'deleted', 'remarks', 'author']

FileFormSet = formset_factory(FileForm, extra=2)

class ApplicantForm(forms.ModelForm):
    firstname = forms.CharField(label='firstname', max_length=80, widget=forms.TextInput(attrs={'class':'form-control form-control-sm', 'placeholder':'first name'}))
    lastname = forms.CharField(label='lastname', max_length=80, widget=forms.TextInput(attrs={'class':'form-control form-control-sm', 'placeholder':'last name'}))
    city = forms.CharField(label='city', max_length=80, widget=forms.TextInput(attrs={'class':'form-control form-control-sm', 'placeholder':'city'}))
    state = forms.CharField(label='state', max_length=2, widget=forms.TextInput(attrs={'class':'form-control form-control-sm', 'placeholder':'--'}))
    area = forms.ModelChoiceField(label='area', required = True, queryset=AreaUS.objects.all(), widget=forms.Select(attrs={'class':'form-control form-control-sm', }),)
    category = forms.ModelChoiceField(label='category', required = True, queryset=Category.objects.all(), widget=forms.Select(attrs={'class':'form-control form-control-sm', }),)
    dispatch_office = forms.CharField(label='dispatch office', max_length=80, widget=forms.TextInput(attrs={'class':'form-control form-control-sm', 'placeholder':'dispatch office'}))
    host_agency = forms.CharField(label='host agency', max_length=80, widget=forms.TextInput(attrs={'class':'form-control form-control-sm', 'placeholder':'host agency'}))
    iqcs = forms.CharField(label='iqcs/iqs', required = True, max_length=80, widget=forms.TextInput(attrs={'class':'form-control form-control-sm', 'placeholder':'############'}))
    work = forms.CharField(label='work', required = False, max_length=20, widget=forms.TextInput(attrs={'class':'form-control form-control-sm', 'placeholder':'### ###-####'}))
    home = forms.CharField(label='home', required = False, max_length=20, widget=forms.TextInput(attrs={'class':'form-control form-control-sm', 'placeholder':'### ###-####'}))
    cell = forms.CharField(label='cell', required = False, max_length=20, widget=forms.TextInput(attrs={'class':'form-control form-control-sm', 'placeholder':'### ###-####'}))
    qualifications = forms.CharField(label='qualifications', required = False, widget=forms.Textarea(attrs={'class':'form-control form-control-sm', 'rows': 2, 'placeholder':'qualifications'}))
    remarks = forms.CharField(label='remarks', required = False, widget=forms.Textarea(attrs={'class':'form-control form-control-sm', 'rows': 2, 'placeholder':'additonal remarks'}))
    supervisor_name = forms.CharField(label='supervisor', max_length=80, widget=forms.TextInput(attrs={'class':'form-control form-control-sm', 'placeholder':'supervisor name'}))
    supervisor_email = forms.CharField(label='supervisor email', max_length=80, widget=forms.TextInput(attrs={'class':'form-control form-control-sm', 'pattern': '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,4}$', 'placeholder':'supervisor@example.com'}))
    admin_name = forms.CharField(label='agency admin', max_length=80, widget=forms.TextInput(attrs={'class':'form-control form-control-sm', 'placeholder':'agency admin name'}))
    admin_email = forms.CharField(label='agency admin email', max_length=80, widget=forms.TextInput(attrs={'class':'form-control form-control-sm', 'pattern': '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,4}$', 'placeholder':'agency_admin@example.com'}))
    training_name = forms.CharField(label='training coordinator', max_length=80, widget=forms.TextInput(attrs={'class':'form-control form-control-sm', 'placeholder':'training coordinator name'}))
    training_email = forms.CharField(label='training coordinator email', max_length=80, widget=forms.TextInput(attrs={'class':'form-control form-control-sm', 'pattern': '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,4}$', 'placeholder':'training_coord@example.com'}))

    class Meta:
        model = Applicant
        exclude = ['created', 'modified', 'applicant', 'author', 'status', 'statused', 'status_author']

class ApplicationForm(forms.ModelForm):
    consideration = forms.ChoiceField(label='consideration', choices=APPLICATION_STATUS_CHOICES, required = True, widget=forms.Select(attrs={'class':'form-control form-control-sm', }),)
    qualifications = forms.CharField(label='qualifications', required = False, widget=forms.Textarea(attrs={'class':'form-control form-control-sm', 'rows': 2, 'placeholder':'qualifications'}))
    remarks = forms.CharField(label='remarks', required = False, widget=forms.Textarea(attrs={'class':'form-control form-control-sm', 'rows': 2, 'placeholder':'additonal remarks'}))
    buy_warrant = forms.NullBooleanField(label='warrant', required=False)
    buy_po = forms.NullBooleanField(label='po', required=False)
    approved_supervisor = forms.NullBooleanField(label='supervisor approval?', required=False, widget=forms.NullBooleanSelect(attrs={'class':'form-control form-control-sm', }),)
    approved_admin = forms.NullBooleanField(label='admin approval?', required=False, widget=forms.NullBooleanSelect(attrs={'class':'form-control form-control-sm', }),)
    approved_training = forms.NullBooleanField(label='training approval?', required=False, widget=forms.NullBooleanSelect(attrs={'class':'form-control form-control-sm', }),)

    class Meta:
        model = Application
        exclude = ['created', 'modified', 'applicant', 'position', 'author', 'e_applied', 'e_supervisor', 'e_training', 'e_admin', 'e_selected', 'a_supervisor', 'a_training', 'a_admin', 'r_supervisor', 'r_training', 'r_admin']
