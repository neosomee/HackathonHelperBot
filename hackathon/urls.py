from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    TeamMemberViewSet,
    TeamViewSet,
    UserViewSet,
    apply_to_team,
    captain_requests,
    create_team,
    list_open_teams,
    register_user,
    team_decision,
    team_detail,
    team_settings,
    update_user_profile,
    user_profile,
)

router = DefaultRouter()
router.register("users", UserViewSet)
router.register("teams", TeamViewSet)
router.register("team-members", TeamMemberViewSet)

urlpatterns = [
    path("register/", register_user, name="register-user"),
    path("profile/<int:telegram_id>/", user_profile, name="user-profile"),
    path("profile/update/", update_user_profile, name="update-user-profile"),
    path("team/create/", create_team, name="create-team"),
    path("team/list/", list_open_teams, name="list-open-teams"),
    path("team/<int:pk>/", team_detail, name="team-detail"),
    path("team/apply/", apply_to_team, name="apply-to-team"),
    path(
        "team/requests/<int:captain_telegram_id>/",
        captain_requests,
        name="captain-requests",
    ),
    path("team/decision/", team_decision, name="team-decision"),
    path("team/settings/", team_settings, name="team-settings"),
    path("", include(router.urls)),
]