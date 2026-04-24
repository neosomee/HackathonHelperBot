from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    extend_schema,
    extend_schema_view,
    inline_serializer,
)
from rest_framework import serializers
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
    UserSerializer, TeamSettingsSerializer,
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
    update_profile, update_team_settings,
)


RegisterUserResponseSerializer = inline_serializer(
    name="RegisterUserResponse",
    fields={
        "created": serializers.BooleanField(),
        "user": UserSerializer(),
    },
)

UserProfileResponseSerializer = inline_serializer(
    name="UserProfileResponse",
    fields={"user": UserSerializer()},
)

TeamResponseSerializer = inline_serializer(
    name="TeamResponse",
    fields={"team": TeamSerializer()},
)

TeamListResponseSerializer = inline_serializer(
    name="TeamListResponse",
    fields={"teams": TeamSerializer(many=True)},
)

TeamDetailResponseSerializer = inline_serializer(
    name="TeamDetailResponse",
    fields={
        "team": TeamSerializer(),
        "members": TeamMemberSerializer(many=True),
    },
)

TeamMemberResponseSerializer = inline_serializer(
    name="TeamMemberResponse",
    fields={"application": TeamMemberSerializer()},
)

TeamRequestsResponseSerializer = inline_serializer(
    name="TeamRequestsResponse",
    fields={"requests": TeamMemberSerializer(many=True)},
)

TELEGRAM_ID_PARAMETER = OpenApiParameter(
    name="telegram_id",
    type=OpenApiTypes.INT,
    location=OpenApiParameter.PATH,
    description="Telegram user ID",
)

TEAM_ID_PARAMETER = OpenApiParameter(
    name="pk",
    type=OpenApiTypes.INT,
    location=OpenApiParameter.PATH,
    description="Unique identifier of the team",
)

CAPTAIN_TELEGRAM_ID_PARAMETER = OpenApiParameter(
    name="captain_telegram_id",
    type=OpenApiTypes.INT,
    location=OpenApiParameter.PATH,
    description="Telegram ID of the team captain",
)

REGISTER_EXAMPLE = OpenApiExample(
    "Register user",
    value={
        "telegram_id": 123456789,
        "full_name": "Ivan Ivanov",
        "email": "ivan@example.com",
        "skills": "Python, Django",
    },
    request_only=True,
)

UPDATE_PROFILE_EXAMPLE = OpenApiExample(
    "Update profile",
    value={
        "telegram_id": 123456789,
        "full_name": "Ivan Ivanov",
        "email": "ivan@example.com",
        "skills": "Python, Django, REST API",
    },
    request_only=True,
)

CREATE_TEAM_EXAMPLE = OpenApiExample(
    "Create team",
    value={
        "captain_telegram_id": 123456789,
        "name": "Backend Builders",
        "description": "We build a hackathon assistant",
        "tech_stack": "Python, Django, PostgreSQL",
        "vacancies": "Frontend, Designer",
    },
    request_only=True,
)

APPLY_TO_TEAM_EXAMPLE = OpenApiExample(
    "Apply to team",
    value={
        "user_telegram_id": 987654321,
        "team_id": 1,
    },
    request_only=True,
)

TEAM_DECISION_EXAMPLE = OpenApiExample(
    "Accept application",
    value={
        "captain_telegram_id": 123456789,
        "user_telegram_id": 987654321,
        "team_id": 1,
        "decision": "accept",
    },
    request_only=True,
)


def service_error_response(error):
    return Response({"error": error.message}, status=error.status_code)


@extend_schema(
    summary="Register user",
    description="Registers or updates a user from Telegram bot registration.",
    tags=["Users"],
    request=RegisterUserSerializer,
    responses={200: RegisterUserResponseSerializer, 201: RegisterUserResponseSerializer},
)
@api_view(["POST"])
def register_user(request):
    serializer = RegisterUserSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    try:
        user, created = register_user_service(
            telegram_id=data["telegram_id"],
            full_name=data["full_name"],
            email=data.get("email", ""),
            skills=data.get("skills", ""),
            is_kaptain=data.get("is_kaptain", False),
        )
    except ServiceError as exc:
        return service_error_response(exc)

    response_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return Response({"created": created, "user": UserSerializer(user).data}, status=response_status)


@extend_schema(
    summary="Get user profile",
    description=(
        "Returns profile data for a user identified by Telegram ID. "
        "Returns 404 if the user has not registered yet."
    ),
    tags=["Users"],
    parameters=[TELEGRAM_ID_PARAMETER],
    responses={200: UserProfileResponseSerializer},
)
@api_view(["GET"])
def user_profile(request, telegram_id):
    try:
        user = get_profile(telegram_id=telegram_id)
    except ServiceError as exc:
        return service_error_response(exc)

    return Response({"user": UserSerializer(user).data})


@extend_schema(
    summary="Update user profile",
    description=(
        "Updates profile fields for an existing user. At least one editable "
        "field must be provided: full_name, email, or skills."
    ),
    tags=["Users"],
    request=UpdateUserProfileSerializer,
    responses={200: UserProfileResponseSerializer},
    examples=[UPDATE_PROFILE_EXAMPLE],
)
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


@extend_schema(
    summary="Create team",
    description="Creates a new team for a user marked as captain and adds them as accepted member.",
    tags=["Teams"],
    request=CreateTeamSerializer,
    responses={201: TeamResponseSerializer},
)
@api_view(["POST"])
def create_team(request):
    serializer = CreateTeamSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    try:
        team = create_team_service(
            captain_telegram_id=data["captain_telegram_id"],
            name=data["name"],
            description=data.get("description", ""),
            tech_stack=data.get("tech_stack", ""),
            vacancies=data.get("vacancies", ""),
            max_members=data.get("max_members", 5),
        )
    except ServiceError as exc:
        return service_error_response(exc)

    return Response({"team": TeamSerializer(team).data}, status=status.HTTP_201_CREATED)


@extend_schema(
    summary="List open teams",
    description=(
        "Returns all teams that are currently open for new applications. "
        "Closed teams are not included in this list."
    ),
    tags=["Teams"],
    responses={200: TeamListResponseSerializer},
)
@api_view(["GET"])
def list_open_teams(request):
    teams = list_open_teams_service()
    return Response({"teams": TeamSerializer(teams, many=True).data})


@extend_schema(
    summary="Get team details",
    description=(
        "Returns detailed information about a team, including captain data "
        "and current team membership/application records."
    ),
    tags=["Teams"],
    parameters=[TEAM_ID_PARAMETER],
    responses={200: TeamDetailResponseSerializer},
)
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


@extend_schema(
    summary="Apply to team",
    description=(
        "Creates a pending application for the selected team. The endpoint "
        "rejects duplicate applications to the same team and does not allow "
        "users who are already accepted members of a team to apply again."
    ),
    tags=["Applications"],
    request=ApplyToTeamSerializer,
    responses={201: TeamMemberResponseSerializer},
    examples=[APPLY_TO_TEAM_EXAMPLE],
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


@extend_schema(
    summary="List captain requests",
    description=(
        "Returns pending incoming applications for all teams owned by the "
        "captain identified by captain_telegram_id. This endpoint is used by "
        "captains to review users who want to join their teams."
    ),
    tags=["Applications"],
    parameters=[CAPTAIN_TELEGRAM_ID_PARAMETER],
    responses={200: TeamRequestsResponseSerializer},
)
@api_view(["GET"])
def captain_requests(request, captain_telegram_id):
    try:
        requests = get_captain_requests(captain_telegram_id=captain_telegram_id)
    except ServiceError as exc:
        return service_error_response(exc)

    return Response({"requests": TeamMemberSerializer(requests, many=True).data})


@extend_schema(
    summary="Accept or reject application",
    description=(
        "Accepts or rejects a pending team application. Only the team captain "
        "can process the application, and only applications in PENDING status "
        "can be processed. Accepting the application makes the user an "
        "accepted team member; rejecting it changes the application status to "
        "rejected."
    ),
    tags=["Applications"],
    request=TeamDecisionSerializer,
    responses={200: TeamMemberResponseSerializer},
    examples=[TEAM_DECISION_EXAMPLE],
)
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

@extend_schema(
    summary="Update team settings",
    description="Allows the captain to open or close recruitment and update team size limit.",
    tags=["Teams"],
    request=TeamSettingsSerializer,
    responses={200: TeamResponseSerializer},
)
@api_view(["POST"])
def team_settings(request):
    serializer = TeamSettingsSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    try:
        team = update_team_settings(
            captain_telegram_id=data["captain_telegram_id"],
            team_id=data["team_id"],
            is_open=data.get("is_open"),
            max_members=data.get("max_members"),
        )
    except ServiceError as exc:
        return service_error_response(exc)

    return Response({"team": TeamSerializer(team).data})


@extend_schema_view(
    list=extend_schema(
        summary="List users",
        description="Returns users stored in the hackathon backend.",
        tags=["Users"],
    ),
    retrieve=extend_schema(
        summary="Get user by ID",
        description="Returns a user by internal database ID.",
        tags=["Users"],
    ),
    create=extend_schema(
        summary="Create user",
        description="Creates a user through the generic DRF endpoint.",
        tags=["Users"],
    ),
    update=extend_schema(
        summary="Update user",
        description="Updates all editable fields for a user by internal ID.",
        tags=["Users"],
    ),
    partial_update=extend_schema(
        summary="Partially update user",
        description="Updates selected fields for a user by internal ID.",
        tags=["Users"],
    ),
    destroy=extend_schema(
        summary="Delete user",
        description="Deletes a user by internal database ID.",
        tags=["Users"],
    ),
)
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer


@extend_schema_view(
    list=extend_schema(
        summary="List all teams",
        description="Returns all teams, including open and closed teams.",
        tags=["Teams"],
    ),
    retrieve=extend_schema(
        summary="Get team by ID",
        description="Returns a team by internal database ID.",
        tags=["Teams"],
    ),
    create=extend_schema(
        summary="Create team through generic endpoint",
        description="Creates a team through the generic DRF endpoint.",
        tags=["Teams"],
    ),
    update=extend_schema(
        summary="Update team",
        description="Updates all editable fields for a team by internal ID.",
        tags=["Teams"],
    ),
    partial_update=extend_schema(
        summary="Partially update team",
        description="Updates selected fields for a team by internal ID.",
        tags=["Teams"],
    ),
    destroy=extend_schema(
        summary="Delete team",
        description="Deletes a team by internal database ID.",
        tags=["Teams"],
    ),
)
class TeamViewSet(viewsets.ModelViewSet):
    queryset = Team.objects.select_related("captain").all()
    serializer_class = TeamSerializer


@extend_schema_view(
    list=extend_schema(
        summary="List team applications and memberships",
        description="Returns team membership records and applications.",
        tags=["Applications"],
    ),
    retrieve=extend_schema(
        summary="Get application or membership by ID",
        description="Returns a team membership/application record by internal ID.",
        tags=["Applications"],
    ),
    create=extend_schema(
        summary="Create application or membership",
        description="Creates a team membership/application through the generic DRF endpoint.",
        tags=["Applications"],
    ),
    update=extend_schema(
        summary="Update application or membership",
        description="Updates all editable fields for a membership/application record.",
        tags=["Applications"],
    ),
    partial_update=extend_schema(
        summary="Partially update application or membership",
        description="Updates selected fields for a membership/application record.",
        tags=["Applications"],
    ),
    destroy=extend_schema(
        summary="Delete application or membership",
        description="Deletes a membership/application record by internal database ID.",
        tags=["Applications"],
    ),
)
class TeamMemberViewSet(viewsets.ModelViewSet):
    queryset = TeamMember.objects.select_related("user", "team").all()
    serializer_class = TeamMemberSerializer
