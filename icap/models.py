import datetime
import uuid

from django.db import models
from django.db.models import Manager as GeoManager
from django.contrib.gis.db.models import GeometryField
from django.contrib.auth.models import User, Group
from django.utils.translation import ugettext_lazy as _
from django.core.files.storage import FileSystemStorage
from django.utils.text import slugify
from taggit.managers import TaggableManager
from django.conf import settings

fs = FileSystemStorage(location=settings.UFS)

def get_userpath(instance, filename):
    return str(instance.user.username + "/" + filename)

def make_uuid():
    return str(uuid.uuid4())

def get_path(instance, filename):
    ext = filename.split('.')[-1]
    front = filename.split('.')[0]
    front = slugify(front)
    filename = "%s-%s.%s" % (front, uuid.uuid4(), ext)
    return str(filename)

LOGITEM_CHOICES = (
    ('D', 'Debug'),
    ('I', 'Info'),
    ('S', 'Success'),
    ('W', 'Warning'),
    ('E', 'Error'),
)

POSITION_STATUS_CHOICES = (
    ('C', 'Closed'),
    ('O', 'Open'),
)

CONSIDERATION_CHOICES = (
    ('P', 'PRIMARY'),
    ('S', 'SHARED'),
    ('A', 'ALTERNATE'),
    ('T', 'TRAINEE'),
    ('W', 'WITHDRAWN'),
)

APPLICATION_STATUS_CHOICES = (
    ('P', 'PRIMARY'),
    ('S', 'SHARED'),
    ('A', 'ALTERNATE'),
    ('T', 'TRAINEE'),
    ('R', 'REJECTED'),
    ('W', 'WITHDRAWN'),
)

class Logitem(models.Model):
    created = models.DateTimeField('created', auto_now_add=True)
    author = models.ForeignKey(User, on_delete=models.PROTECT)
    status = models.CharField('status', max_length=1, choices=LOGITEM_CHOICES)
    message = models.TextField('message',)
    obj_model = models.CharField('model', max_length=80, help_text="object model.", )
    obj_id = models.CharField('object id', max_length=999, help_text="object id.", )
    obj_in = models.TextField('object in', blank=True, null=True, help_text="serialized in.", )
    obj_out = models.TextField('object out', blank=True, null=True, help_text="serialized out.", )

    class Meta:
        db_table = 'icap_logitem'
        verbose_name = _('log item')
        verbose_name_plural = _('log items')
        ordering = ('-created',)

class AreaUS(models.Model):
    created = models.DateTimeField('created', auto_now_add=True)
    modified = models.DateTimeField('modified', auto_now=True, blank=True, null=True)
    deleted = models.NullBooleanField('delete?')
    author = models.ForeignKey(User, on_delete=models.PROTECT, related_name="area_author")
    name = models.CharField('name', max_length=80, blank=True, null=True, help_text="")
    slug = models.CharField('slug', max_length=80, blank=True, null=True, help_text="")
    open_date = models.DateTimeField('effective open', blank=True, null=True, help_text="")
    close_date = models.DateTimeField('effective close', blank=True, null=True, help_text="")
    contact = models.CharField('contact', max_length=80, blank=True, null=True, help_text="")
    phone = models.CharField('phone', max_length=20, blank=True, null=True, help_text="")
    remarks = models.TextField('remarks', max_length=10240, blank=True, null=True, help_text="", )
    tags = TaggableManager(blank=True,)

    class Meta:
        db_table = 'icap_area'
        verbose_name = _('area')
        verbose_name_plural = _('areas')
        ordering = ('name',)

    def __str__(self):
        return u"%s" % (self.name)

    def get_absolute_url(self):
        return "/%s/" % (self.slug)

class Team(models.Model):
    created = models.DateTimeField('created', auto_now_add=True)
    modified = models.DateTimeField('modified', auto_now=True, blank=True, null=True)
    deleted = models.NullBooleanField('delete?')
    author = models.ForeignKey(User, on_delete=models.PROTECT, related_name="team_author")
    name = models.CharField('name', max_length=80, blank=True, null=True, help_text="")
    slug = models.CharField('slug', max_length=80, blank=True, null=True, help_text="")
    area = models.ForeignKey(AreaUS, on_delete=models.PROTECT, related_name="team_area")
    open_date = models.DateTimeField('effective open', blank=True, null=True, help_text="")
    close_date = models.DateTimeField('effective close', blank=True, null=True, help_text="")
    remarks = models.TextField('remarks', max_length=10240, blank=True, null=True, help_text="", )
    pool = models.NullBooleanField('allow selection to any area team?')
    tags = TaggableManager(blank=True,)

    class Meta:
        db_table = 'icap_team'
        verbose_name = _('team')
        verbose_name_plural = _('teams')
        ordering = ('name',)

    def __str__(self):
        return u"%s" % (self.name)

    def get_absolute_url(self):
        return "/%s/%s/" % (self.area.slug, self.slug)

class Position(models.Model):
    created = models.DateTimeField('created', auto_now_add=True)
    modified = models.DateTimeField('modified', auto_now=True, blank=True, null=True)
    deleted = models.NullBooleanField('delete?')
    author = models.ForeignKey(User, on_delete=models.PROTECT, related_name="position_author")
    code = models.CharField('code', max_length=80, blank=True, null=True, help_text="")
    name = models.CharField('name', max_length=80, blank=True, null=True, help_text="")
    slug = models.CharField('slug', max_length=80, blank=True, null=True, help_text="")
    team = models.ForeignKey(Team, on_delete=models.PROTECT, related_name="position_team")
    remarks = models.TextField('remarks', max_length=10240, blank=True, null=True, help_text="", )
    supervisor_approval = models.NullBooleanField('require supervisor approval?')
    admin_approval = models.NullBooleanField('require agency admin approval?')
    training_approval = models.NullBooleanField('require training coordinator approval?')
    out_of_area = models.NullBooleanField('accept out-of-area applicants?')
    international = models.NullBooleanField('accept international applicants?')
    buying_team = models.NullBooleanField('require buying team questions?')
    open_date = models.DateTimeField('effective open', blank=True, null=True, help_text="")
    close_date = models.DateTimeField('effective close', blank=True, null=True, help_text="")
    tags = TaggableManager(blank=True,)

    class Meta:
        db_table = 'icap_position'
        verbose_name = _('position')
        verbose_name_plural = _('positions')
        ordering = ('name',)

    def __str__(self):
        return u"%s" % (self.name)

    def get_absolute_url(self):
        return "/%s/%s/%s/" % (self.team.area.slug, self.team.slug, self.slug)

class PositionStatus(models.Model):
    created = models.DateTimeField('created', auto_now_add=True)
    modified = models.DateTimeField('modified', auto_now=True, blank=True, null=True)
    author = models.ForeignKey(User, on_delete=models.PROTECT)
    position = models.ForeignKey(Position, on_delete=models.PROTECT, related_name="positionstatus_position")
    status = models.CharField('status', max_length=1, choices=POSITION_STATUS_CHOICES)
    effective = models.DateTimeField('effective', auto_now_add=False)

    class Meta:
        db_table = 'icap_position_status'
        verbose_name = _('position status')
        verbose_name_plural = _('position statuses')
        ordering = ('-created',)

    def __str__(self):
        return u"%s %s %s" % (self.position.team.area.slug, self.position.team.slug, self.position.slug)

class Category(models.Model):
    created = models.DateTimeField('created', auto_now_add=True)
    modified = models.DateTimeField('modified', auto_now=True, blank=True, null=True)
    deleted = models.NullBooleanField('delete?')
    author = models.ForeignKey(User, on_delete=models.PROTECT, related_name="category_author")
    name = models.CharField('name', max_length=80, blank=True, null=True, help_text="")
    slug = models.CharField('slug', max_length=80, blank=True, null=True, help_text="")
    area = models.ForeignKey(AreaUS, on_delete=models.PROTECT, related_name="category_area")
    remarks = models.TextField('remarks', max_length=10240, blank=True, null=True, help_text="", )

    class Meta:
        db_table = 'icap_category'
        verbose_name = _('category')
        verbose_name_plural = _('categories')
        ordering = ('name',)

    def __str__(self):
        return u"%s" % (self.name)

class Applicant(models.Model):
    created = models.DateTimeField('created', auto_now_add=True)
    modified = models.DateTimeField('modified', auto_now=True, blank=True, null=True)
    author = models.ForeignKey(User, on_delete=models.PROTECT)
    firstname = models.CharField('firstname', max_length=80, blank=True, null=True, help_text="")
    lastname = models.CharField('lastname', max_length=80, blank=True, null=True, help_text="")
    area = models.ForeignKey(AreaUS, on_delete=models.PROTECT, related_name="applicant_area", null=True)
    city = models.CharField('city', max_length=80, blank=True, null=True, help_text="")
    state = models.CharField('state', max_length=2, blank=True, null=True, help_text="")
    #zipcode = models.CharField('zip', max_length=10, blank=True, null=True, help_text="")
    #email = models.EmailField('email', max_length=80, blank=True, null=True, help_text="")
    work = models.CharField('work phone', max_length=20, blank=True, null=True, help_text="")
    home = models.CharField('home phone', max_length=20, blank=True, null=True, help_text="")
    cell = models.CharField('cell phone', max_length=20, blank=True, null=True, help_text="")
    #pager = models.CharField('pager', max_length=20, blank=True, null=True, help_text="")
    #fax = models.CharField('fax phone', max_length=20, blank=True, null=True, help_text="")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="applicant_category", null=True)
    iqcs = models.CharField('iqcs', max_length=80, blank=True, null=True, help_text="")
    qualifications = models.TextField('qualifications', max_length=10240, blank=True, null=True, help_text="", )
    dispatch_office = models.CharField('dispatch office', max_length=80, blank=True, null=True, help_text="")
    #dispatch = models.CharField('dispatch phone', max_length=20, blank=True, null=True, help_text="")
    host_agency = models.CharField('host agency', max_length=80, blank=True, null=True, help_text="")
    #host_address = models.CharField('host agency', max_length=80, blank=True, null=True, help_text="")
    supervisor_name = models.CharField('supervisor name', max_length=80, blank=True, null=True, help_text="")
    supervisor_email = models.EmailField('supervisor email', max_length=80, blank=True, null=True, help_text="")
    admin_name = models.CharField('admin name', max_length=80, blank=True, null=True, help_text="")
    admin_email = models.EmailField('admin email', max_length=80, blank=True, null=True, help_text="")
    training_name = models.CharField('training name', max_length=80, blank=True, null=True, help_text="")
    training_email = models.EmailField('training email', max_length=80, blank=True, null=True, help_text="")
    remarks = models.TextField('remarks', max_length=10240, blank=True, null=True, help_text="", )

    class Meta:
        db_table = 'icap_applicant'
        verbose_name = _('applicant')
        verbose_name_plural = _('applicants')
        ordering = ('lastname','firstname',)

    def __str__(self):
        return u"%s %s" % (self.firstname, self.lastname)

class File(models.Model):
    created = models.DateTimeField('created', auto_now_add=True)
    modified = models.DateTimeField('modified', auto_now=True, blank=True, null=True)
    deleted = models.NullBooleanField('delete?')
    author = models.ForeignKey(User, on_delete=models.PROTECT)
    applicant = models.ForeignKey(Applicant, on_delete=models.CASCADE, related_name='files')
    afile = models.FileField('File', max_length=500, storage=fs, upload_to=get_path, blank=True,)
    remarks = models.TextField('Remarks', max_length=1024, blank=True, null=True, help_text="Enter comments you want to accompany this row of data.", )
    tags = TaggableManager(blank=True,)

    class Meta:
        db_table = 'icap_file'
        verbose_name = _('file')
        verbose_name_plural = _('files')
        ordering = ('-created','afile',)

    def __str__(self):
        return u"%s" % (self.afile.name)

class Application(models.Model):
    created = models.DateTimeField('created', auto_now_add=True)
    modified = models.DateTimeField('modified', auto_now=True, blank=True, null=True)
    deleted = models.NullBooleanField('delete?')
    author = models.ForeignKey(User, on_delete=models.PROTECT)
    applicant = models.ForeignKey(Applicant, on_delete=models.PROTECT, related_name="application_applicant")
    position = models.ForeignKey(Position, on_delete=models.PROTECT, related_name="application_position")
    consideration = models.CharField('consideration', max_length=1, choices=CONSIDERATION_CHOICES)
    buy_warrant = models.CharField('warrant', max_length=80, blank=True, null=True, help_text="")
    buy_po = models.CharField('po', max_length=80, blank=True, null=True, help_text="")
    qualifications = models.TextField('qualifications', max_length=10240, blank=True, null=True, help_text="", )
    remarks = models.TextField('remarks', max_length=10240, blank=True, null=True, help_text="", )
    approved_supervisor = models.NullBooleanField('supervisor approval?')
    approved_admin = models.NullBooleanField('admin approval?')
    approved_training = models.NullBooleanField('training approval?')
    status = models.CharField('status', max_length=1, choices=APPLICATION_STATUS_CHOICES, blank=True, null=True)
    status_author = models.ForeignKey(User, on_delete=models.PROTECT, blank=True, null=True, related_name="application_status_author")
    statused = models.DateTimeField('statused', blank=True, null=True)

    class Meta:
        db_table = 'icap_application'
        verbose_name = _('application')
        verbose_name_plural = _('applications')
        ordering = ('-created',)

    def __str__(self):
        return u"%s %s %s %s" % (self.applicant.firstname, self.applicant.lastname, self.position.name, self.position.team.name)

class ApplicationStatus(models.Model):
    created = models.DateTimeField('created', auto_now_add=True)
    modified = models.DateTimeField('modified', auto_now=True, blank=True, null=True)
    author = models.ForeignKey(User, on_delete=models.PROTECT)
    application = models.ForeignKey(Application, on_delete=models.PROTECT, related_name="applicationstatus_application")
    status = models.CharField('status', max_length=1, choices=APPLICATION_STATUS_CHOICES)
    effective = models.DateTimeField('effective', auto_now_add=False)

    class Meta:
        db_table = 'icap_application_status'
        verbose_name = _('application status')
        verbose_name_plural = _('application statuses')
        ordering = ('-created',)

    def __str__(self):
        return u"%s" % (self.status)
