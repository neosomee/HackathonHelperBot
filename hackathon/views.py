from django.http import HttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    extend_schema,
    extend_schema_view,
    inline_serializer,
)
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .exports import build_participants_workbook, build_teams_workbook
from .models import Team, TeamMember, User
from .serializers import (
    ApplyToTeamSerializer,
    CreateHackathonSerializer,
    CreateTeamSerializer,
    DeleteProfileSerializer,
    DeleteTeamSerializer,
    HackathonReadSerializer,
    JoinHackathonSerializer,
    LeaveTeamSerializer,
    RegisterUserSerializer,
    ScheduleSubscribeSerializer,
    TeamDecisionSerializer,
    TeamMemberSerializer,
    TeamSettingsSerializer,
    TeamSerializer,
    TransferCaptainSerializer,
    UpdateUserProfileSerializer,
    UserSerializer,
)
from .services import (
    ServiceError,
    apply_to_team as apply_to_team_service,
    captain_join_hackathon,
    create_hackathon_by_user,
    create_team as create_team_service,
    decide_team_request,
    delete_profile as delete_profile_service,
    delete_team as delete_team_service,
    get_captain_requests,
    get_profile,
    get_team_detail,
    hackathon_permissions_for_telegram_id,
    hackathon_schedule_now_next,
    leave_team as leave_team_service,
    list_hackathons_for_join,
    list_hackathons_organized_by,
    list_open_teams as list_open_teams_service,
    register_user as register_user_service,
    subscribe_hackathon_schedule,
    transfer_captain as transfer_captain_service,
    unsubscribe_hackathon_schedule,
    update_profile,
    update_team_settings,
    user_hackathons_schedule_overview,
    user_organizes_hackathon,
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
            can_create_hackathons=data.get("can_create_hackathons", False),
        )
    except ServiceError as exc:
        return service_error_response(exc)

    response_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return Response({"created": created, "user": UserSerializer(user).data}, status=response_status)


@extend_schema(
    summary="Get user profile",
    description="Returns profile data for a user identified by Telegram ID.",
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
    description="Updates profile fields for an existing user.",
    tags=["Users"],
    request=UpdateUserProfileSerializer,
    responses={200: UserProfileResponseSerializer},
    examples=[UPDATE_PROFILE_EXAMPLE],
)
@api_view(["POST"])
def update_user_profile(request):
    serializer = UpdateUserProfileSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

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
    tags=["Teams"],
    request=CreateTeamSerializer,
    responses={201: TeamResponseSerializer},
    examples=[CREATE_TEAM_EXAMPLE],
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
    tags=["Teams"],
    responses={200: TeamListResponseSerializer},
)
@api_view(["GET"])
def list_open_teams(request):
    teams = list_open_teams_service()
    return Response({"teams": TeamSerializer(teams, many=True).data})


@extend_schema(
    summary="Get team details",
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
    tags=["Applications"],
    request=ApplyToTeamSerializer,
    responses={201: TeamMemberResponseSerializer},
    examples=[APPLY_TO_TEAM_EXAMPLE],
)
@api_view(["POST"])
def apply_to_team(request):
    serializer = ApplyToTeamSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

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
    tags=["Applications"],
    request=TeamDecisionSerializer,
    responses={200: TeamMemberResponseSerializer},
    examples=[TEAM_DECISION_EXAMPLE],
)
@api_view(["POST"])
def team_decision(request):
    serializer = TeamDecisionSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

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
            name=data.get("name"),
            description=data.get("description"),
            tech_stack=data.get("tech_stack"),
            vacancies=data.get("vacancies"),
            is_open=data.get("is_open"),
            max_members=data.get("max_members"),
        )
    except ServiceError as exc:
        return service_error_response(exc)

    return Response({"team": TeamSerializer(team).data})


@extend_schema(
    summary="Leave team",
    tags=["Teams"],
    request=LeaveTeamSerializer,
)
@api_view(["POST"])
def leave_team_view(request):
    serializer = LeaveTeamSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    try:
        leave_team_service(user_telegram_id=data["user_telegram_id"])
    except ServiceError as exc:
        return service_error_response(exc)

    return Response({"success": True})


@extend_schema(
    summary="Transfer captaincy",
    tags=["Teams"],
    request=TransferCaptainSerializer,
)
@api_view(["POST"])
def transfer_captain_view(request):
    serializer = TransferCaptainSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    try:
        team = transfer_captain_service(
            captain_telegram_id=data["captain_telegram_id"],
            team_id=data["team_id"],
            new_captain_telegram_id=data["new_captain_telegram_id"],
        )
    except ServiceError as exc:
        return service_error_response(exc)

    return Response({"team": TeamSerializer(team).data})


@extend_schema(
    summary="Delete team",
    tags=["Teams"],
    request=DeleteTeamSerializer,
)
@api_view(["POST"])
def delete_team_view(request):
    serializer = DeleteTeamSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    try:
        delete_team_service(
            captain_telegram_id=data["captain_telegram_id"],
            team_id=data["team_id"],
        )
    except ServiceError as exc:
        return service_error_response(exc)

    return Response({"success": True})


@extend_schema(
    summary="Delete profile",
    tags=["Users"],
    request=DeleteProfileSerializer,
)
@api_view(["POST"])
def delete_profile_view(request):
    serializer = DeleteProfileSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    try:
        delete_profile_service(telegram_id=data["telegram_id"])
    except ServiceError as exc:
        return service_error_response(exc)

    return Response({"success": True})


@extend_schema(
    summary="Hackathon permissions for Telegram user",
    tags=["Hackathons"],
)
@api_view(["GET"])
def hackathon_permissions(request):
    raw = request.query_params.get("telegram_id")
    if not raw or not raw.isdigit():
        return Response({"error": "telegram_id is required."}, status=status.HTTP_400_BAD_REQUEST)

    return Response(hackathon_permissions_for_telegram_id(telegram_id=int(raw)))


@extend_schema(
    summary="Create hackathon",
    tags=["Hackathons"],
    request=CreateHackathonSerializer,
)
@api_view(["POST"])
def hackathon_create(request):
    serializer = CreateHackathonSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    try:
        hackathon = create_hackathon_by_user(
            telegram_id=data["telegram_id"],
            name=data["name"],
            description=data.get("description") or "",
            schedule_sheet_url=data.get("schedule_sheet_url") or "",
            is_team_join_open=data.get("is_team_join_open", True),
        )
    except ServiceError as exc:
        return service_error_response(exc)

    return Response({"hackathon": HackathonReadSerializer(hackathon).data}, status=status.HTTP_201_CREATED)


@extend_schema(
    summary="List hackathons for team join",
    tags=["Hackathons"],
)
@api_view(["GET"])
def hackathon_list(request):
    captain_raw = request.query_params.get("captain_telegram_id")
    user_raw = request.query_params.get("user_telegram_id")

    captain_id = int(captain_raw) if captain_raw and captain_raw.isdigit() else None
    user_id = int(user_raw) if user_raw and user_raw.isdigit() else None

    rows = list_hackathons_for_join(
        captain_telegram_id=captain_id,
        user_telegram_id=user_id,
    )
    return Response({"hackathons": rows})


@extend_schema(
    summary="List hackathons organized by user",
    tags=["Hackathons"],
)
@api_view(["GET"])
def hackathon_organized_list(request):
    raw = request.query_params.get("telegram_id")
    if not raw or not raw.isdigit():
        return Response({"error": "telegram_id is required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        qs = list_hackathons_organized_by(telegram_id=int(raw))
    except ServiceError as exc:
        return Response({"error": exc.message}, status=exc.status_code)

    return Response(
        {
            "hackathons": [
                {"id": h.id, "name": h.name, "slug": h.slug}
                for h in qs
            ]
        }
    )


@extend_schema(
    summary="Captain joins team to hackathon",
    tags=["Hackathons"],
    request=JoinHackathonSerializer,
)
@api_view(["POST"])
def hackathon_join_team(request, pk):
    serializer = JoinHackathonSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    try:
        link = captain_join_hackathon(
            captain_telegram_id=serializer.validated_data["captain_telegram_id"],
            hackathon_id=pk,
        )
    except ServiceError as exc:
        return service_error_response(exc)

    return Response(
        {
            "hackathon_id": link.hackathon_id,
            "team_id": link.team_id,
            "joined_at": link.joined_at,
        },
        status=status.HTTP_201_CREATED,
    )


@extend_schema(
    summary="Subscribe to hackathon schedule",
    tags=["Hackathons"],
    request=ScheduleSubscribeSerializer,
)
@api_view(["POST"])
def hackathon_schedule_subscribe(request, pk):
    serializer = ScheduleSubscribeSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    try:
        subscribe_hackathon_schedule(
            telegram_id=serializer.validated_data["telegram_id"],
            hackathon_id=pk,
        )
    except ServiceError as exc:
        return service_error_response(exc)

    return Response({"subscribed": True})


@extend_schema(
    summary="Unsubscribe from hackathon schedule",
    tags=["Hackathons"],
    request=ScheduleSubscribeSerializer,
)
@api_view(["POST"])
def hackathon_schedule_unsubscribe(request, pk):
    serializer = ScheduleSubscribeSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    try:
        unsubscribe_hackathon_schedule(
            telegram_id=serializer.validated_data["telegram_id"],
            hackathon_id=pk,
        )
    except ServiceError as exc:
        return service_error_response(exc)

    return Response({"subscribed": False})


def _schedule_event_payload(ev):
    if ev is None:
        return None
    return {
        "title": ev.title,
        "description": ev.description,
        "start": ev.start.isoformat(),
        "notify_minutes_before": ev.notify_minutes_before,
    }


@extend_schema(
    summary="Current and next schedule events",
    tags=["Hackathons"],
    parameters=[
        OpenApiParameter(
            name="telegram_id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            required=True,
        ),
    ],
)
@api_view(["GET"])
def hackathon_schedule_status(request, pk):
    raw = request.query_params.get("telegram_id")
    if not raw or not raw.isdigit():
        return Response({"error": "telegram_id is required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        hackathon, current, upcoming = hackathon_schedule_now_next(
            telegram_id=int(raw),
            hackathon_id=pk,
        )
    except ServiceError as exc:
        return service_error_response(exc)

    return Response(
        {
            "hackathon_id": hackathon.id,
            "hackathon_name": hackathon.name,
            "current": _schedule_event_payload(current),
            "next": _schedule_event_payload(upcoming),
        }
    )


@extend_schema(
    summary="User enrolled hackathons",
    tags=["Hackathons"],
    parameters=[
        OpenApiParameter(
            name="telegram_id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            required=True,
        ),
    ],
)
@api_view(["GET"])
def user_hackathons_schedule_list(request):
    raw = request.query_params.get("telegram_id")
    if not raw or not raw.isdigit():
        return Response({"error": "telegram_id is required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        rows = user_hackathons_schedule_overview(telegram_id=int(raw))
    except ServiceError as exc:
        return service_error_response(exc)

    return Response({"hackathons": rows})


@extend_schema(
    summary="Export hackathon data to Excel",
    tags=["Hackathons"],
    parameters=[
        OpenApiParameter(
            name="telegram_id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            required=True,
        ),
        OpenApiParameter(
            name="kind",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=True,
        ),
    ],
)
@api_view(["GET"])
def hackathon_export(request, pk):
    telegram_raw = request.query_params.get("telegram_id")
    kind = (request.query_params.get("kind") or "").lower()

    if not telegram_raw or not telegram_raw.isdigit():
        return HttpResponse("telegram_id required", status=400)
    if kind not in ("participants", "teams"):
        return HttpResponse("kind must be participants or teams", status=400)

    try:
        _, hackathon = user_organizes_hackathon(
            telegram_id=int(telegram_raw),
            hackathon_id=pk,
        )
    except ServiceError as exc:
        return HttpResponse(exc.message, status=exc.status_code)

    if kind == "participants":
        payload = build_participants_workbook(hackathon)
        filename = f"hackathon_{hackathon.slug}_participants.xlsx"
    else:
        payload = build_teams_workbook(hackathon)
        filename = f"hackathon_{hackathon.slug}_teams.xlsx"

    response = HttpResponse(
        payload,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@extend_schema_view(
    list=extend_schema(tags=["Users"]),
    retrieve=extend_schema(tags=["Users"]),
    create=extend_schema(tags=["Users"]),
    update=extend_schema(tags=["Users"]),
    partial_update=extend_schema(tags=["Users"]),
    destroy=extend_schema(tags=["Users"]),
)
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer


@extend_schema_view(
    list=extend_schema(tags=["Teams"]),
    retrieve=extend_schema(tags=["Teams"]),
    create=extend_schema(tags=["Teams"]),
    update=extend_schema(tags=["Teams"]),
    partial_update=extend_schema(tags=["Teams"]),
    destroy=extend_schema(tags=["Teams"]),
)
class TeamViewSet(viewsets.ModelViewSet):
    queryset = Team.objects.select_related("captain").all()
    serializer_class = TeamSerializer


@extend_schema_view(
    list=extend_schema(tags=["Applications"]),
    retrieve=extend_schema(tags=["Applications"]),
    create=extend_schema(tags=["Applications"]),
    update=extend_schema(tags=["Applications"]),
    partial_update=extend_schema(tags=["Applications"]),
    destroy=extend_schema(tags=["Applications"]),
)
class TeamMemberViewSet(viewsets.ModelViewSet):
    queryset = TeamMember.objects.select_related("user", "team").all()
    serializer_class = TeamMemberSerializer