from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import TeamMemberViewSet, TeamViewSet, UserViewSet

router = DefaultRouter()
router.register("users", UserViewSet)
router.register("teams", TeamViewSet)
router.register("team-members", TeamMemberViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
