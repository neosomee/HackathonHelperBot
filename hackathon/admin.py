from django.contrib import admin

from .models import Team, TeamMember, User


class TeamMemberInline(admin.TabularInline):
    model = TeamMember
    extra = 0
    fields = ("user", "status", "created_at")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("user",)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "telegram_id",
        "email",
        "role",
        "is_active",
        "created_at",
    )
    list_filter = ("role", "is_active", "created_at")
    search_fields = ("full_name", "email", "telegram_id", "skills")
    readonly_fields = ("created_at",)
    ordering = ("full_name",)


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "captain_name",
        "tech_stack",
        "vacancies",
        "is_open",
        "created_at",
    )
    list_filter = ("is_open", "created_at")
    search_fields = (
        "name",
        "description",
        "tech_stack",
        "vacancies",
        "captain__full_name",
        "captain__telegram_id",
    )
    readonly_fields = ("created_at",)
    autocomplete_fields = ("captain",)
    inlines = (TeamMemberInline,)
    ordering = ("name",)

    @admin.display(description="Captain", ordering="captain__full_name")
    def captain_name(self, obj):
        return obj.captain.full_name


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = (
        "user_name",
        "team_name",
        "captain_name",
        "status",
        "created_at",
    )
    list_filter = (
        "status",
        "team__is_open",
        "team__captain__role",
        "created_at",
    )
    search_fields = (
        "user__full_name",
        "user__telegram_id",
        "team__name",
        "team__captain__full_name",
    )
    readonly_fields = ("created_at",)
    autocomplete_fields = ("user", "team")
    ordering = ("-created_at",)

    @admin.display(description="User", ordering="user__full_name")
    def user_name(self, obj):
        return obj.user.full_name

    @admin.display(description="Team", ordering="team__name")
    def team_name(self, obj):
        return obj.team.name

    @admin.display(description="Captain", ordering="team__captain__full_name")
    def captain_name(self, obj):
        return obj.team.captain.full_name
