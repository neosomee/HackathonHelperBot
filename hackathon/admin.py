from django.contrib import admin

from .models import Team, TeamMember, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("full_name", "telegram_id", "email", "role", "is_active", "created_at")
    list_filter = ("role", "is_active", "created_at")
    search_fields = ("full_name", "email", "telegram_id", "skills")
    readonly_fields = ("created_at",)


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "captain", "is_open", "created_at")
    list_filter = ("is_open", "created_at")
    search_fields = ("name", "description", "tech_stack", "vacancies")
    readonly_fields = ("created_at",)


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ("user", "team", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("user__full_name", "team__name")
    readonly_fields = ("created_at",)
