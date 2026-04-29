from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    UserViewSet,
    TeamViewSet,
    TeamMemberViewSet,

    register_user,
    user_profile,
    update_user_profile,
    delete_profile_view,

    create_team,
    list_open_teams,
    team_detail,
    apply_to_team,
    captain_requests,
    team_decision,
    team_settings,
    leave_team_view,
    transfer_captain_view,
    delete_team_view,

    hackathon_permissions,
    hackathon_create,
    hackathon_list,
    hackathon_organized_list,
    hackathon_join_team,
    hackathon_export,
    hackathon_schedule_subscribe,
    hackathon_schedule_unsubscribe,
    hackathon_schedule_status,
    user_hackathons_schedule_list,
    hackathon_detail,
    hackathon_organizer_dashboard,
    hackathon_update,
    hackathon_delete,
)

router = DefaultRouter()
router.register("users", UserViewSet)
router.register("teams", TeamViewSet)
router.register("team-members", TeamMemberViewSet)

urlpatterns = [
    path("register/", register_user, name="register-user"),
    path("profile/<int:telegram_id>/", user_profile, name="user-profile"),
    path("profile/update/", update_user_profile, name="update-user-profile"),
    path("profile/delete/", delete_profile_view, name="delete-profile"),

    path("team/create/", create_team, name="create-team"),
    path("team/list/", list_open_teams, name="list-open-teams"),
    path("team/<int:pk>/", team_detail, name="team-detail"),
    path("team/apply/", apply_to_team, name="apply-to-team"),
    path("team/requests/<int:captain_telegram_id>/", captain_requests, name="captain-requests"),
    path("team/decision/", team_decision, name="team-decision"),
    path("team/settings/", team_settings, name="team-settings"),
    path("team/leave/", leave_team_view, name="leave-team"),
    path("team/transfer-captain/", transfer_captain_view, name="transfer-captain"),
    path("team/delete/", delete_team_view, name="delete-team"),

    path("hackathons/permissions/", hackathon_permissions, name="hackathon-permissions"),
    path("hackathons/create/", hackathon_create, name="hackathon-create"),
    path("hackathons/", hackathon_list, name="hackathon-list"),
    path("hackathons/organized/", hackathon_organized_list, name="hackathon-organized-list"),
    path("hackathons/my-schedule/", user_hackathons_schedule_list, name="user-hackathons-schedule-list"),

    path("hackathons/<int:pk>/", hackathon_detail, name="hackathon-detail"),
    path("hackathons/<int:pk>/dashboard/", hackathon_organizer_dashboard, name="hackathon-organizer-dashboard"),
    path("hackathons/<int:pk>/update/", hackathon_update, name="hackathon-update"),
    path("hackathons/<int:pk>/delete/", hackathon_delete, name="hackathon-delete"),

    path("hackathons/<int:pk>/join-team/", hackathon_join_team, name="hackathon-join-team"),
    path("hackathons/<int:pk>/export/", hackathon_export, name="hackathon-export"),
    path("hackathons/<int:pk>/schedule/subscribe/", hackathon_schedule_subscribe, name="hackathon-schedule-subscribe"),
    path("hackathons/<int:pk>/schedule/unsubscribe/", hackathon_schedule_unsubscribe, name="hackathon-schedule-unsubscribe"),
    path("hackathons/<int:pk>/schedule/status/", hackathon_schedule_status, name="hackathon-schedule-status"),

    path("", include(router.urls)),
]