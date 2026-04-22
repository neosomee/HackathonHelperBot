from dataclasses import dataclass

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from rest_framework import status

from .models import Team, TeamMember, User


@dataclass
class ServiceError(Exception):
    message: str
    status_code: int = status.HTTP_400_BAD_REQUEST


def user_has_team(user):
    return (
        Team.objects.filter(captain=user).exists()
        or TeamMember.objects.filter(
            user=user,
            status=TeamMember.Status.ACCEPTED,
        ).exists()
    )


def require_positive_int(value, field_name):
    if value is None:
        raise ServiceError(f"{field_name} is required.")

    try:
        value = int(value)
    except (TypeError, ValueError) as exc:
        raise ServiceError(f"{field_name} must be a number.") from exc

    if value <= 0:
        raise ServiceError(f"{field_name} must be greater than zero.")

    return value


def require_not_blank(value, field_name, *, max_length=None):
    if value is None:
        raise ServiceError(f"{field_name} is required.")

    value = str(value).strip()
    if not value:
        raise ServiceError(f"{field_name} cannot be empty.")

    if max_length is not None and len(value) > max_length:
        raise ServiceError(f"{field_name} is too long.")

    return value


def optional_not_blank(value, field_name, *, max_length=None):
    if value is None:
        return None
    return require_not_blank(value, field_name, max_length=max_length)


def require_valid_email(value, field_name="email"):
    value = require_not_blank(value, field_name)
    try:
        validate_email(value)
    except DjangoValidationError as exc:
        raise ServiceError("Enter a valid email address.") from exc
    return value


def optional_valid_email(value, field_name="email"):
    if value is None:
        return None
    return require_valid_email(value, field_name)


def register_user(*, telegram_id, full_name, email="", skills=""):
    telegram_id = require_positive_int(telegram_id, "telegram_id")
    full_name = require_not_blank(full_name, "full_name", max_length=255)
    email = require_valid_email(email)
    skills = require_not_blank(skills, "skills")

    user, created = User.objects.update_or_create(
        telegram_id=telegram_id,
        defaults={
            "full_name": full_name,
            "email": email,
            "skills": skills,
            "is_active": True,
        },
    )
    return user, created


def get_profile(*, telegram_id):
    telegram_id = require_positive_int(telegram_id, "telegram_id")

    try:
        return User.objects.get(telegram_id=telegram_id)
    except User.DoesNotExist as exc:
        raise ServiceError("User not found.", status.HTTP_404_NOT_FOUND) from exc


def update_profile(*, telegram_id, full_name=None, email=None, skills=None):
    telegram_id = require_positive_int(telegram_id, "telegram_id")
    full_name = optional_not_blank(full_name, "full_name", max_length=255)
    email = optional_valid_email(email)
    skills = optional_not_blank(skills, "skills")

    user = get_profile(telegram_id=telegram_id)
    update_fields = []

    for field, value in (
        ("full_name", full_name),
        ("email", email),
        ("skills", skills),
    ):
        if value is not None:
            setattr(user, field, value)
            update_fields.append(field)

    if not update_fields:
        raise ServiceError(
            "Provide at least one profile field: full_name, email, or skills.",
            status.HTTP_400_BAD_REQUEST,
        )

    user.save(update_fields=update_fields)
    return user


def create_team(
    *,
    captain_telegram_id,
    name,
    description="",
    tech_stack="",
    vacancies="",
):
    captain_telegram_id = require_positive_int(
        captain_telegram_id,
        "captain_telegram_id",
    )
    name = require_not_blank(name, "name", max_length=255)
    description = require_not_blank(description, "description")
    tech_stack = require_not_blank(tech_stack, "tech_stack")
    vacancies = require_not_blank(vacancies, "vacancies")

    try:
        captain = User.objects.get(telegram_id=captain_telegram_id)
    except User.DoesNotExist as exc:
        raise ServiceError("Captain user not found.", status.HTTP_404_NOT_FOUND) from exc

    if user_has_team(captain):
        raise ServiceError("User is already in a team.", status.HTTP_409_CONFLICT)

    with transaction.atomic():
        if captain.role == User.Role.PARTICIPANT:
            captain.role = User.Role.CAPTAIN
            captain.save(update_fields=["role"])

        team = Team.objects.create(
            captain=captain,
            name=name,
            description=description,
            tech_stack=tech_stack,
            vacancies=vacancies,
        )
        TeamMember.objects.create(
            user=captain,
            team=team,
            status=TeamMember.Status.ACCEPTED,
        )
    return team


def list_open_teams():
    return Team.objects.select_related("captain").filter(is_open=True)


def get_team_detail(*, team_id):
    team_id = require_positive_int(team_id, "team_id")

    try:
        team = Team.objects.select_related("captain").get(pk=team_id)
    except Team.DoesNotExist as exc:
        raise ServiceError("Team not found.", status.HTTP_404_NOT_FOUND) from exc

    members = TeamMember.objects.select_related("user", "team", "team__captain").filter(
        team=team
    )
    return team, members


def apply_to_team(*, user_telegram_id, team_id):
    user_telegram_id = require_positive_int(user_telegram_id, "user_telegram_id")
    team_id = require_positive_int(team_id, "team_id")

    try:
        user = User.objects.get(telegram_id=user_telegram_id)
    except User.DoesNotExist as exc:
        raise ServiceError("User not found.", status.HTTP_404_NOT_FOUND) from exc

    try:
        team = Team.objects.get(pk=team_id)
    except Team.DoesNotExist as exc:
        raise ServiceError("Team not found.", status.HTTP_404_NOT_FOUND) from exc

    if not team.is_open:
        raise ServiceError("Team is closed.", status.HTTP_409_CONFLICT)

    if TeamMember.objects.filter(user=user, team=team).exists():
        raise ServiceError("Application already exists.", status.HTTP_409_CONFLICT)

    if user_has_team(user):
        raise ServiceError("User is already in a team.", status.HTTP_409_CONFLICT)

    try:
        return TeamMember.objects.create(
            user=user,
            team=team,
            status=TeamMember.Status.PENDING,
        )
    except IntegrityError as exc:
        raise ServiceError("Application already exists.", status.HTTP_409_CONFLICT) from exc


def get_captain_requests(*, captain_telegram_id):
    captain_telegram_id = require_positive_int(
        captain_telegram_id,
        "captain_telegram_id",
    )

    try:
        captain = User.objects.get(telegram_id=captain_telegram_id)
    except User.DoesNotExist as exc:
        raise ServiceError("Captain user not found.", status.HTTP_404_NOT_FOUND) from exc

    return TeamMember.objects.select_related("user", "team", "team__captain").filter(
        team__captain=captain,
        status=TeamMember.Status.PENDING,
    )


def decide_team_request(*, captain_telegram_id, user_telegram_id, team_id, decision):
    captain_telegram_id = require_positive_int(
        captain_telegram_id,
        "captain_telegram_id",
    )
    user_telegram_id = require_positive_int(user_telegram_id, "user_telegram_id")
    team_id = require_positive_int(team_id, "team_id")

    if decision not in ("accept", "reject"):
        raise ServiceError("decision must be either accept or reject.")

    try:
        captain = User.objects.get(telegram_id=captain_telegram_id)
    except User.DoesNotExist as exc:
        raise ServiceError("Captain user not found.", status.HTTP_404_NOT_FOUND) from exc

    try:
        user = User.objects.get(telegram_id=user_telegram_id)
    except User.DoesNotExist as exc:
        raise ServiceError("User not found.", status.HTTP_404_NOT_FOUND) from exc

    try:
        team = Team.objects.get(pk=team_id)
    except Team.DoesNotExist as exc:
        raise ServiceError("Team not found.", status.HTTP_404_NOT_FOUND) from exc

    if team.captain_id != captain.id:
        raise ServiceError(
            "Only the team captain can process this request.",
            status.HTTP_403_FORBIDDEN,
        )

    try:
        application = TeamMember.objects.get(user=user, team=team)
    except TeamMember.DoesNotExist as exc:
        raise ServiceError("Application not found.", status.HTTP_404_NOT_FOUND) from exc

    if application.status != TeamMember.Status.PENDING:
        raise ServiceError(
            "Application has already been processed.",
            status.HTTP_409_CONFLICT,
        )

    if decision == "accept" and user_has_team(user):
        raise ServiceError("User is already in a team.", status.HTTP_409_CONFLICT)

    application.status = (
        TeamMember.Status.ACCEPTED
        if decision == "accept"
        else TeamMember.Status.REJECTED
    )
    application.save(update_fields=["status"])
    return application
