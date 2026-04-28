from dataclasses import dataclass

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.db import transaction
from rest_framework import status

from bot.notifications import (
    notify_application_result,
    notify_captain_transferred,
    notify_member_left,
    notify_new_application,
    notify_team_closed_status,
    notify_team_created,
    notify_team_deleted,
)

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


def register_user(*, telegram_id, full_name, email="", skills="", is_kaptain=False):
    telegram_id = require_positive_int(telegram_id, "telegram_id")
    full_name = require_not_blank(full_name, "full_name", max_length=255)
    email = require_valid_email(email)
    skills = require_not_blank(skills, "skills")

    with transaction.atomic():
        user, created = User.objects.update_or_create(
            telegram_id=telegram_id,
            defaults={
                "full_name": full_name,
                "email": email,
                "skills": skills,
                "is_kaptain": bool(is_kaptain),
                "role": User.Role.CAPTAIN if is_kaptain else User.Role.PARTICIPANT,
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
    max_members=5,
):
    captain_telegram_id = require_positive_int(captain_telegram_id, "captain_telegram_id")
    name = require_not_blank(name, "name", max_length=255)
    description = require_not_blank(description, "description")
    tech_stack = require_not_blank(tech_stack, "tech_stack")
    vacancies = require_not_blank(vacancies, "vacancies")

    try:
        captain = User.objects.get(telegram_id=captain_telegram_id)
    except User.DoesNotExist as exc:
        raise ServiceError("Captain user not found.", status.HTTP_404_NOT_FOUND) from exc

    if not captain.is_kaptain:
        raise ServiceError("Only captain users can create a team.", status.HTTP_403_FORBIDDEN)

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
            max_members=max_members or 5,
        )

        TeamMember.objects.create(
            user=captain,
            team=team,
            status=TeamMember.Status.ACCEPTED,
        )

        transaction.on_commit(lambda: notify_team_created(team))

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

    accepted_count = TeamMember.objects.filter(
        team=team,
        status=TeamMember.Status.ACCEPTED,
    ).count()

    if team.max_members and accepted_count >= team.max_members:
        raise ServiceError("Team is full.", status.HTTP_409_CONFLICT)

    if TeamMember.objects.filter(user=user, team=team).exists():
        raise ServiceError("Application already exists.", status.HTTP_409_CONFLICT)

    if user_has_team(user):
        raise ServiceError("User is already in a team.", status.HTTP_409_CONFLICT)

    with transaction.atomic():
        application = TeamMember.objects.create(
            user=user,
            team=team,
            status=TeamMember.Status.PENDING,
        )
        transaction.on_commit(lambda: notify_new_application(application))

    return application


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
    captain_telegram_id = require_positive_int(captain_telegram_id, "captain_telegram_id")
    user_telegram_id = require_positive_int(user_telegram_id, "user_telegram_id")
    team_id = require_positive_int(team_id, "team_id")

    if decision not in ("accept", "reject"):
        raise ServiceError("Decision must be accept or reject.", status.HTTP_400_BAD_REQUEST)

    try:
        captain = User.objects.get(telegram_id=captain_telegram_id)
    except User.DoesNotExist as exc:
        raise ServiceError("Captain user not found.", status.HTTP_404_NOT_FOUND) from exc

    try:
        team = Team.objects.get(pk=team_id)
    except Team.DoesNotExist as exc:
        raise ServiceError("Team not found.", status.HTTP_404_NOT_FOUND) from exc

    if team.captain != captain:
        raise ServiceError("Only team captain can decide requests.", status.HTTP_403_FORBIDDEN)

    try:
        application = TeamMember.objects.select_related("user", "team").get(
            user__telegram_id=user_telegram_id,
            team_id=team_id,
            status=TeamMember.Status.PENDING,
        )
    except TeamMember.DoesNotExist as exc:
        raise ServiceError("Pending application not found.", status.HTTP_404_NOT_FOUND) from exc

    accepted = False

    if decision == "accept":
        accepted_count = TeamMember.objects.filter(
            team=team,
            status=TeamMember.Status.ACCEPTED,
        ).count()

        if team.max_members and accepted_count >= team.max_members:
            raise ServiceError("Team is full.", status.HTTP_409_CONFLICT)

        other_team_membership = TeamMember.objects.filter(
            user=application.user,
            status=TeamMember.Status.ACCEPTED,
        ).exclude(team=team).exists()

        if other_team_membership:
            raise ServiceError("User is already in a team.", status.HTTP_409_CONFLICT)

        application.status = TeamMember.Status.ACCEPTED
        accepted = True
    else:
        application.status = TeamMember.Status.REJECTED

    with transaction.atomic():
        application.save(update_fields=["status"])
        transaction.on_commit(lambda: notify_application_result(application, accepted=accepted))

    return application


def update_team_settings(
    *,
    captain_telegram_id,
    team_id,
    name=None,
    description=None,
    tech_stack=None,
    vacancies=None,
    is_open=None,
    max_members=None,
):
    captain_telegram_id = require_positive_int(captain_telegram_id, "captain_telegram_id")
    team_id = require_positive_int(team_id, "team_id")

    name = optional_not_blank(name, "name", max_length=255)
    description = optional_not_blank(description, "description")
    tech_stack = optional_not_blank(tech_stack, "tech_stack")
    vacancies = optional_not_blank(vacancies, "vacancies")

    try:
        captain = User.objects.get(telegram_id=captain_telegram_id)
    except User.DoesNotExist as exc:
        raise ServiceError("Captain user not found.", status.HTTP_404_NOT_FOUND) from exc

    try:
        team = Team.objects.get(pk=team_id)
    except Team.DoesNotExist as exc:
        raise ServiceError("Team not found.", status.HTTP_404_NOT_FOUND) from exc

    if team.captain != captain:
        raise ServiceError("Only team captain can update settings.", status.HTTP_403_FORBIDDEN)

    update_fields = []
    was_open = team.is_open

    if name is not None:
        team.name = name
        update_fields.append("name")

    if description is not None:
        team.description = description
        update_fields.append("description")

    if tech_stack is not None:
        team.tech_stack = tech_stack
        update_fields.append("tech_stack")

    if vacancies is not None:
        team.vacancies = vacancies
        update_fields.append("vacancies")

    if is_open is not None:
        team.is_open = bool(is_open)
        update_fields.append("is_open")

    if max_members is not None:
        accepted_count = TeamMember.objects.filter(
            team=team,
            status=TeamMember.Status.ACCEPTED,
        ).count()

        max_members = int(max_members)

        if max_members < accepted_count:
            raise ServiceError(
                "Max members cannot be lower than current accepted members.",
                status.HTTP_409_CONFLICT,
            )

        team.max_members = max_members
        update_fields.append("max_members")

    if not update_fields:
        raise ServiceError("No settings to update.", status.HTTP_400_BAD_REQUEST)

    team.save(update_fields=update_fields)

    if is_open is not None and was_open != team.is_open:
        transaction.on_commit(lambda: notify_team_closed_status(team))

    return team


def leave_team(*, user_telegram_id):
    user_telegram_id = require_positive_int(user_telegram_id, "user_telegram_id")

    try:
        user = User.objects.get(telegram_id=user_telegram_id)
    except User.DoesNotExist as exc:
        raise ServiceError("User not found.", status.HTTP_404_NOT_FOUND) from exc

    accepted_membership = TeamMember.objects.select_related("team").filter(
        user=user,
        status=TeamMember.Status.ACCEPTED,
    ).first()

    if not accepted_membership:
        raise ServiceError("User is not in a team.", status.HTTP_409_CONFLICT)

    team = accepted_membership.team

    if team.captain == user:
        raise ServiceError(
            "Captain cannot leave the team. Transfer captaincy or delete the team.",
            status.HTTP_409_CONFLICT,
        )

    remaining_members = list(
        TeamMember.objects.select_related("user").filter(
            team=team,
            status=TeamMember.Status.ACCEPTED,
        )
    )

    with transaction.atomic():
        TeamMember.objects.filter(user=user, team=team).delete()
        transaction.on_commit(lambda: notify_member_left(team, user, remaining_members))

    return True


def transfer_captain(*, captain_telegram_id, team_id, new_captain_telegram_id):
    captain_telegram_id = require_positive_int(captain_telegram_id, "captain_telegram_id")
    team_id = require_positive_int(team_id, "team_id")
    new_captain_telegram_id = require_positive_int(
        new_captain_telegram_id,
        "new_captain_telegram_id",
    )

    try:
        captain = User.objects.get(telegram_id=captain_telegram_id)
    except User.DoesNotExist as exc:
        raise ServiceError("Captain user not found.", status.HTTP_404_NOT_FOUND) from exc

    try:
        team = Team.objects.select_related("captain").get(pk=team_id)
    except Team.DoesNotExist as exc:
        raise ServiceError("Team not found.", status.HTTP_404_NOT_FOUND) from exc

    if team.captain != captain:
        raise ServiceError("Only team captain can transfer captaincy.", status.HTTP_403_FORBIDDEN)

    try:
        new_captain = User.objects.get(telegram_id=new_captain_telegram_id)
    except User.DoesNotExist as exc:
        raise ServiceError("New captain user not found.", status.HTTP_404_NOT_FOUND) from exc

    is_team_member = TeamMember.objects.filter(
        user=new_captain,
        team=team,
        status=TeamMember.Status.ACCEPTED,
    ).exists()

    if not is_team_member:
        raise ServiceError(
            "New captain must be an accepted member of the same team.",
            status.HTTP_409_CONFLICT,
        )

    old_captain = captain

    with transaction.atomic():
        team.captain = new_captain
        team.save(update_fields=["captain"])

        old_captain.role = User.Role.PARTICIPANT
        old_captain.save(update_fields=["role"])

        new_captain.role = User.Role.CAPTAIN
        new_captain.save(update_fields=["role"])

        transaction.on_commit(
            lambda: notify_captain_transferred(
                team,
                old_captain=old_captain,
                new_captain=new_captain,
            )
        )

    return team


def delete_team(*, captain_telegram_id, team_id):
    captain_telegram_id = require_positive_int(captain_telegram_id, "captain_telegram_id")
    team_id = require_positive_int(team_id, "team_id")

    try:
        captain = User.objects.get(telegram_id=captain_telegram_id)
    except User.DoesNotExist:
        raise ServiceError("Captain not found.", status.HTTP_404_NOT_FOUND)

    try:
        team = Team.objects.get(pk=team_id)
    except Team.DoesNotExist:
        raise ServiceError("Team not found.", status.HTTP_404_NOT_FOUND)

    if team.captain != captain:
        raise ServiceError("Only captain can delete team.", status.HTTP_403_FORBIDDEN)

    members = list(TeamMember.objects.select_related("user").filter(team=team))

    with transaction.atomic():
        TeamMember.objects.filter(team=team).delete()
        team.delete()

        captain.role = User.Role.PARTICIPANT
        captain.save(update_fields=["role"])

        transaction.on_commit(lambda: notify_team_deleted(team, members))

    return True


def delete_profile(*, telegram_id):
    telegram_id = require_positive_int(telegram_id, "telegram_id")

    try:
        user = User.objects.get(telegram_id=telegram_id)
    except User.DoesNotExist as exc:
        raise ServiceError("User not found.", status.HTTP_404_NOT_FOUND) from exc

    with transaction.atomic():
        team = Team.objects.filter(captain=user).first()

        if team:
            members = list(TeamMember.objects.select_related("user").filter(team=team))
            TeamMember.objects.filter(team=team).delete()
            team.delete()
            transaction.on_commit(lambda: notify_team_deleted(team, members))

        TeamMember.objects.filter(user=user).delete()
        user.delete()

    return True