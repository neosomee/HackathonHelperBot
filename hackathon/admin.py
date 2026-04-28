from django.contrib import admin

from .models import (
    Hackathon,
    HackathonScheduleSubscription,
    HackathonTeam,
    ScheduleNotificationLog,
    Team,
    TeamMember,
    User,
)


class TeamMemberInline(admin.TabularInline):
    model = TeamMember
    extra = 0
    fields = ("user", "status", "created_at")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("user",)


class HackathonTeamInline(admin.TabularInline):
    model = HackathonTeam
    extra = 0
    autocomplete_fields = ("team",)
    readonly_fields = ("joined_at",)


@admin.register(Hackathon)
class HackathonAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_team_join_open", "created_at")
    list_filter = ("is_team_join_open", "created_at")
    search_fields = ("name", "slug", "description")
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ("organizers",)
    readonly_fields = ("created_at", "updated_at")
    inlines = (HackathonTeamInline,)
    fieldsets = (
        (None, {"fields": ("name", "slug", "description")}),
        ("Расписание и доступ", {"fields": ("schedule_sheet_url", "is_team_join_open", "organizers", "created_by")}),
        ("Служебное", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(HackathonTeam)
class HackathonTeamAdmin(admin.ModelAdmin):
    list_display = ("hackathon", "team", "joined_at")
    list_filter = ("hackathon",)
    search_fields = ("team__name", "hackathon__name")
    autocomplete_fields = ("hackathon", "team")


@admin.register(HackathonScheduleSubscription)
class HackathonScheduleSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "hackathon", "is_active", "updated_at")
    list_filter = ("is_active", "hackathon")
    search_fields = ("user__telegram_id", "user__full_name", "hackathon__name")
    autocomplete_fields = ("user", "hackathon")


@admin.register(ScheduleNotificationLog)
class ScheduleNotificationLogAdmin(admin.ModelAdmin):
    list_display = ("user", "hackathon", "dedupe_key", "sent_at")
    list_filter = ("hackathon",)
    search_fields = ("dedupe_key", "user__telegram_id")
    readonly_fields = ("sent_at",)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "telegram_id",
        "email",
        "role",
        "can_create_hackathons",
        "is_active",
        "created_at",
    )
    list_filter = ("role", "can_create_hackathons", "is_active", "created_at")
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
