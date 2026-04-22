from rest_framework import viewsets

from .models import Team, TeamMember, User
from .serializers import TeamMemberSerializer, TeamSerializer, UserSerializer


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class TeamViewSet(viewsets.ModelViewSet):
    queryset = Team.objects.select_related("captain").all()
    serializer_class = TeamSerializer


class TeamMemberViewSet(viewsets.ModelViewSet):
    queryset = TeamMember.objects.select_related("user", "team").all()
    serializer_class = TeamMemberSerializer
