from django.contrib import admin
from guardian.admin import GuardedModelAdmin

from icap.models import *

class LogitemAdmin(admin.ModelAdmin):
    date_hierarchy = 'created'
    list_display = ('message', 'status', 'created', 'author',)
    list_per_page = 50
    list_filter = ('status', 'obj_model', 'author', )
    save_as = True

admin.site.register(Logitem, LogitemAdmin)

class AreaUSAdmin(GuardedModelAdmin):
    date_hierarchy = 'created'
    list_display = ('name', 'slug', 'open_date', 'close_date', 'contact', 'phone', 'deleted',)
    ordering = ['name',]
    list_per_page = 50
    list_filter = ('deleted',)
    save_as = True

admin.site.register(AreaUS, AreaUSAdmin)

class TeamAdmin(admin.ModelAdmin):
    date_hierarchy = 'created'
    list_display = ('name', 'area', 'open_date', 'close_date', 'pool', 'deleted',)
    ordering = ['name', 'area',]
    list_per_page = 50
    list_filter = ('area', 'pool', 'deleted')
    save_as = True

admin.site.register(Team, TeamAdmin)

class PositionAdmin(admin.ModelAdmin):
    date_hierarchy = 'created'
    list_display = ('code', 'name', 'team', 'team_area', 'open_date', 'close_date', 'deleted',)
    list_per_page = 50
    list_filter = ('team__area', 'team', 'code', 'deleted',)
    list_display_links = ('code', 'name',)
    list_editable = ('open_date', 'close_date',)
    save_as = True

    def team_area(self, obj):
        return obj.team.area

    team_area.admin_order_field = 'area'
    team_area.short_description = 'Area'

admin.site.register(Position, PositionAdmin)

class PositionStatusAdmin(admin.ModelAdmin):
    date_hierarchy = 'created'
    list_display = ('position', 'position_team', 'position_team_area', 'status', 'effective', 'author',)
    list_per_page = 50
    list_filter = ('position__team__area', 'status', 'author', )
    save_as = True

    def position_team(self, obj):
        return obj.position.team

    position_team.admin_order_field = 'position__team'
    position_team.short_description = 'Team'

    def position_team_area(self, obj):
        return obj.position.team.area

    position_team_area.admin_order_field = 'position__team__area'
    position_team_area.short_description = 'Area'

admin.site.register(PositionStatus, PositionStatusAdmin)

class CategoryAdmin(admin.ModelAdmin):
    date_hierarchy = 'created'
    list_display = ('name', 'slug', 'area', 'deleted', 'author',)
    list_per_page = 50
    list_filter = ('area', 'deleted',)
    save_as = True

admin.site.register(Category, CategoryAdmin)

class ApplicantAdmin(admin.ModelAdmin):
    date_hierarchy = 'created'
    list_display = ('firstname', 'lastname', 'author', 'area', 'category', 'host_agency')
    list_per_page = 50
    list_filter = ('area', 'category')
    list_display_links = ('firstname', 'lastname', 'author')
    save_as = True

admin.site.register(Applicant, ApplicantAdmin)

class FileAdmin(admin.ModelAdmin):
    date_hierarchy = 'created'
    #list_display = ('afile', 'afile_size', 'applicant_firstname', 'applicant_lastname', 'author',)
    list_per_page = 50
    list_filter = ('author', )
    save_as = True

    def applicant_firstname(self, obj):
        return obj.applicant.firstname

    applicant_firstname.admin_order_field = 'applicant__firstname'
    applicant_firstname.short_description = 'firstname'

    def applicant_lastname(self, obj):
        return obj.applicant.lastname

    applicant_lastname.admin_order_field = 'applicant__lastname'
    applicant_lastname.short_description = 'lastname'

    def afile_size(self, obj):
        return obj.afile.size

    afile_size.short_description = 'size'

admin.site.register(File, FileAdmin)

class ApplicationAdmin(admin.ModelAdmin):
    date_hierarchy = 'created'
    list_display = ('application_applicant_firstname', 'application_applicant_lastname', 'position_team_area', 'position_team', 'position', 'consideration', 'status',)
    list_per_page = 50
    list_filter = ('position__team__area', 'consideration', 'status',)
    list_display_links = ('application_applicant_firstname', 'application_applicant_lastname',)
    search_fields = ['applicant__lastname']
    save_as = True

    def application_applicant_firstname(self, obj):
        return obj.applicant.firstname

    application_applicant_firstname.admin_order_field = 'applicant__firstname'
    application_applicant_firstname.short_description = 'firstname'

    def application_applicant_lastname(self, obj):
        return obj.applicant.lastname

    application_applicant_lastname.admin_order_field = 'applicant__lastname'
    application_applicant_lastname.short_description = 'lastname'

    def position_team(self, obj):
        return obj.position.team

    position_team.admin_order_field = 'position__team'
    position_team.short_description = 'Team'

    def position_team_area(self, obj):
        return obj.position.team.area

    position_team_area.admin_order_field = 'position__team__area'
    position_team_area.short_description = 'Area'

admin.site.register(Application, ApplicationAdmin)

class ApplicationStatusAdmin(admin.ModelAdmin):
    date_hierarchy = 'created'
    list_display = ('application_applicant_firstname', 'application_applicant_lastname', 'application_position', 'application_position_team', 'application_position_team_area', 'status', 'effective', 'author',)
    list_per_page = 50
    list_filter = ('application__position__team__area', 'status', 'author', )
    list_display_links = ('application_applicant_firstname', 'application_applicant_lastname')
    save_as = True

    def application_applicant_firstname(self, obj):
        return obj.application.applicant.firstname

    application_applicant_firstname.admin_order_field = 'application__applicant__firstname'
    application_applicant_firstname.short_description = 'Firstname'

    def application_applicant_lastname(self, obj):
        return obj.application.applicant.lastname

    application_applicant_lastname.admin_order_field = 'application__applicant__lastname'
    application_applicant_lastname.short_description = 'Lastname'

    def application_position(self, obj):
        return obj.application.position

    application_position.admin_order_field = 'application__position'
    application_position.short_description = 'Position'

    def application_position_team(self, obj):
        return obj.application.position.team

    application_position_team.admin_order_field = 'application__position__team'
    application_position_team.short_description = 'Team'

    def application_position_team_area(self, obj):
        return obj.application.position.team.area

    application_position_team_area.admin_order_field = 'position__team__area'
    application_position_team_area.short_description = 'Area'

admin.site.register(ApplicationStatus, ApplicationStatusAdmin)

class LegacyApplicantAdmin(admin.ModelAdmin):
    date_hierarchy = 'created'
    list_display = ('firstname', 'lastname', 'area', 'category', 'host_agency')
    list_per_page = 50
    list_filter = ('area', 'category')
    list_display_links = ('firstname', 'lastname',)
    save_as = True

admin.site.register(LegacyApplicant, LegacyApplicantAdmin)

class UnitAdmin(admin.ModelAdmin):
    date_hierarchy = 'created'
    list_display = ('name', 'slug', 'wildlandrole', 'unitid', 'unittype', 'deleted',)
    ordering = ['name',]
    list_per_page = 50
    list_filter = ('wildlandrole', 'nation')
    save_as = True

admin.site.register(Unit, UnitAdmin)
