from rest_framework import status, viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Team, TeamMember, User
from .serializers import (
    ApplyToTeamSerializer,
    CreateTeamSerializer,
    RegisterUserSerializer,
    TeamDecisionSerializer,
    TeamMemberSerializer,
    TeamSerializer,
    UpdateUserProfileSerializer,
    UserSerializer,
)
from .services import (
    ServiceError,
    apply_to_team as apply_to_team_service,
    create_team as create_team_service,
    decide_team_request,
    get_captain_requests,
    get_profile,
    get_team_detail,
    list_open_teams as list_open_teams_service,
    register_user as register_user_service,
    update_profile,
)


def service_error_response(error):
    return Response({"error": error.message}, status=error.status_code)


@api_view(["POST"])
def register_user(request):
    serializer = RegisterUserSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    data = serializer.validated_data
    user, created = register_user_service(
        telegram_id=data["telegram_id"],
        full_name=data["full_name"],
        email=data.get("email", ""),
        skills=data.get("skills", ""),
    )

    response_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return Response(
        {
            "created": created,
            "user": UserSerializer(user).data,
        },
        status=response_status,
    )


@api_view(["GET"])
def user_profile(request, telegram_id):
    try:
        user = get_profile(telegram_id=telegram_id)
    except ServiceError as exc:
        return service_error_response(exc)

    return Response({"user": UserSerializer(user).data})


@api_view(["POST"])
def update_user_profile(request):
    serializer = UpdateUserProfileSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    data = serializer.validated_data
    try:
        user = update_profile(
            telegram_id=data["telegram_id"],
            full_name=data.get("full_name"),
            email=data.get("email"),
            skills=data.get("skills"),
        )
    except ServiceError as exc:
        return service_error_response(exc)

    return Response({"user": UserSerializer(user).data})


@api_view(["POST"])
def create_team(request):
    serializer = CreateTeamSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    data = serializer.validated_data
    try:
        team = create_team_service(
            captain_telegram_id=data["captain_telegram_id"],
            name=data["name"],
            description=data.get("description", ""),
            tech_stack=data.get("tech_stack", ""),
            vacancies=data.get("vacancies", ""),
        )
    except ServiceError as exc:
        return service_error_response(exc)

    return Response(
        {"team": TeamSerializer(team).data},
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
def list_open_teams(request):
    teams = list_open_teams_service()
    return Response({"teams": TeamSerializer(teams, many=True).data})


@api_view(["GET"])
def team_detail(request, pk):
    try:
        team, members = get_team_detail(team_id=pk)
    except ServiceError as exc:
        return service_error_response(exc)

    return Response(
        {
            "team": TeamSerializer(team).data,
            "members": TeamMemberSerializer(members, many=True).data,
        }
    )


@api_view(["POST"])
def apply_to_team(request):
    serializer = ApplyToTeamSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    data = serializer.validated_data
    try:
        application = apply_to_team_service(
            user_telegram_id=data["user_telegram_id"],
            team_id=data["team_id"],
        )
    except ServiceError as exc:
        return service_error_response(exc)

    return Response(
        {"application": TeamMemberSerializer(application).data},
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
def captain_requests(request, captain_telegram_id):
    try:
        requests = get_captain_requests(captain_telegram_id=captain_telegram_id)
    except ServiceError as exc:
        return service_error_response(exc)

    return Response({"requests": TeamMemberSerializer(requests, many=True).data})


@api_view(["POST"])
def team_decision(request):
    serializer = TeamDecisionSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    data = serializer.validated_data
    try:
        application = decide_team_request(
            captain_telegram_id=data["captain_telegram_id"],
            user_telegram_id=data["user_telegram_id"],
            team_id=data["team_id"],
            decision=data["decision"],
        )
    except ServiceError as exc:
        return service_error_response(exc)

    return Response({"application": TeamMemberSerializer(application).data})


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class TeamViewSet(viewsets.ModelViewSet):
    queryset = Team.objects.select_related("captain").all()
    serializer_class = TeamSerializer


class TeamMemberViewSet(viewsets.ModelViewSet):
    queryset = TeamMember.objects.select_related("user", "team").all()
    serializer_class = TeamMemberSerializer
