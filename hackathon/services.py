from dataclasses import dataclass

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import URLValidator, validate_email
from django.db import IntegrityError, transaction
from django.utils.text import slugify
from rest_framework import status

from .models import (
    Hackathon,
    HackathonScheduleSubscription,
    HackathonTeam,
    Team,
    TeamMember,
    User,
)


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


def register_user(
    *,
    telegram_id,
    full_name,
    email="",
    skills="",
    is_kaptain=False,
    can_create_hackathons=False,
):
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
                "can_create_hackathons": bool(can_create_hackathons),
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

    return TeamMember.objects.create(
        user=user,
        team=team,
        status=TeamMember.Status.PENDING,
    )


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

    if decision == "accept":
        accepted_count = TeamMember.objects.filter(
            team=team,
            status=TeamMember.Status.ACCEPTED,
        ).count()

        if team.max_members and accepted_count >= team.max_members:
            raise ServiceError("Team is full.", status.HTTP_409_CONFLICT)

        application.status = TeamMember.Status.ACCEPTED
    else:
        application.status = TeamMember.Status.REJECTED

    application.save(update_fields=["status"])
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
    return team


def user_organizes_hackathon(*, telegram_id, hackathon_id):
    user = get_profile(telegram_id=telegram_id)
    try:
        hackathon = Hackathon.objects.get(pk=hackathon_id)
    except Hackathon.DoesNotExist as exc:
        raise ServiceError("Hackathon not found.", status.HTTP_404_NOT_FOUND) from exc

    if not hackathon.organizers.filter(pk=user.pk).exists():
        raise ServiceError("Organizer access denied.", status.HTTP_403_FORBIDDEN)
    return user, hackathon


def list_hackathons_for_join(*, captain_telegram_id=None, user_telegram_id=None):
    qs = (
        Hackathon.objects.filter(is_team_join_open=True)
        .only("id", "name", "slug", "description", "schedule_sheet_url", "is_team_join_open")
        .order_by("-created_at")
    )
    result = []
    captain_team = None
    if captain_telegram_id is not None:
        captain_telegram_id = require_positive_int(captain_telegram_id, "captain_telegram_id")
        try:
            captain = User.objects.get(telegram_id=captain_telegram_id)
        except User.DoesNotExist:
            captain = None
        if captain:
            captain_team = Team.objects.filter(captain=captain).first()

    schedule_user = None
    if user_telegram_id is not None:
        ut = require_positive_int(user_telegram_id, "user_telegram_id")
        schedule_user = User.objects.filter(telegram_id=ut).first()

    for h in qs:
        item = {
            "id": h.id,
            "name": h.name,
            "slug": h.slug,
            "description": h.description,
            "schedule_sheet_url": h.schedule_sheet_url,
            "is_team_join_open": h.is_team_join_open,
            "my_team_enrolled": False,
            "schedule_subscribed": False,
        }
        if captain_team:
            item["my_team_enrolled"] = HackathonTeam.objects.filter(
                hackathon=h,
                team=captain_team,
            ).exists()
        if schedule_user:
            item["schedule_subscribed"] = HackathonScheduleSubscription.objects.filter(
                user=schedule_user,
                hackathon=h,
                is_active=True,
            ).exists()
        result.append(item)
    return result


def list_hackathons_organized_by(*, telegram_id):
    telegram_id = require_positive_int(telegram_id, "telegram_id")
    user = get_profile(telegram_id=telegram_id)
    return (
        Hackathon.objects.filter(organizers=user)
        .only("id", "name", "slug")
        .order_by("-created_at")
    )


def captain_join_hackathon(*, captain_telegram_id, hackathon_id):
    captain_telegram_id = require_positive_int(captain_telegram_id, "captain_telegram_id")
    hackathon_id = require_positive_int(hackathon_id, "hackathon_id")

    try:
        captain = User.objects.get(telegram_id=captain_telegram_id)
    except User.DoesNotExist as exc:
        raise ServiceError("Captain user not found.", status.HTTP_404_NOT_FOUND) from exc

    try:
        hackathon = Hackathon.objects.get(pk=hackathon_id)
    except Hackathon.DoesNotExist as exc:
        raise ServiceError("Hackathon not found.", status.HTTP_404_NOT_FOUND) from exc

    if not hackathon.is_team_join_open:
        raise ServiceError("Hackathon does not accept new teams.", status.HTTP_409_CONFLICT)

    team = Team.objects.filter(captain=captain).first()
    if not team:
        raise ServiceError("Only a team captain with a team can join a hackathon.", status.HTTP_403_FORBIDDEN)

    accepted = TeamMember.objects.filter(
        user=captain,
        team=team,
        status=TeamMember.Status.ACCEPTED,
    ).exists()
    if not accepted:
        raise ServiceError("Captain must be an accepted member of the team.", status.HTTP_403_FORBIDDEN)

    link, created = HackathonTeam.objects.get_or_create(hackathon=hackathon, team=team)
    if not created:
        raise ServiceError("Team is already enrolled in this hackathon.", status.HTTP_409_CONFLICT)
    return link


def user_in_hackathon_network(*, user: User, hackathon: Hackathon) -> bool:
    team_ids = list(
        HackathonTeam.objects.filter(hackathon=hackathon).values_list("team_id", flat=True)
    )
    if not team_ids:
        return False
    return TeamMember.objects.filter(
        user=user,
        team_id__in=team_ids,
        status=TeamMember.Status.ACCEPTED,
    ).exists()


def subscribe_hackathon_schedule(*, telegram_id, hackathon_id):
    telegram_id = require_positive_int(telegram_id, "telegram_id")
    hackathon_id = require_positive_int(hackathon_id, "hackathon_id")
    user = get_profile(telegram_id=telegram_id)
    try:
        hackathon = Hackathon.objects.get(pk=hackathon_id)
    except Hackathon.DoesNotExist as exc:
        raise ServiceError("Hackathon not found.", status.HTTP_404_NOT_FOUND) from exc

    if not (hackathon.schedule_sheet_url or "").strip():
        raise ServiceError(
            "Schedule URL is not configured for this hackathon.",
            status.HTTP_400_BAD_REQUEST,
        )

    if not user_in_hackathon_network(user=user, hackathon=hackathon):
        raise ServiceError(
            "Only members of teams enrolled in this hackathon can subscribe to schedule alerts.",
            status.HTTP_403_FORBIDDEN,
        )

    HackathonScheduleSubscription.objects.update_or_create(
        user=user,
        hackathon=hackathon,
        defaults={"is_active": True},
    )


def unsubscribe_hackathon_schedule(*, telegram_id, hackathon_id):
    telegram_id = require_positive_int(telegram_id, "telegram_id")
    hackathon_id = require_positive_int(hackathon_id, "hackathon_id")
    user = get_profile(telegram_id=telegram_id)
    try:
        hackathon = Hackathon.objects.get(pk=hackathon_id)
    except Hackathon.DoesNotExist as exc:
        raise ServiceError("Hackathon not found.", status.HTTP_404_NOT_FOUND) from exc

    sub = HackathonScheduleSubscription.objects.filter(user=user, hackathon=hackathon).first()
    if not sub:
        raise ServiceError("Subscription not found.", status.HTTP_404_NOT_FOUND)

    sub.is_active = False
    sub.save(update_fields=["is_active", "updated_at"])


def can_create_hackathon_for_user(user: User) -> bool:
    if user.can_create_hackathons:
        return True
    if user.organized_hackathons.exists():
        return True
    bootstrap = getattr(settings, "ORGANIZER_BOOTSTRAP_TELEGRAM_IDS", frozenset())
    return user.telegram_id in bootstrap


def hackathon_permissions_for_telegram_id(*, telegram_id):
    telegram_id = require_positive_int(telegram_id, "telegram_id")
    try:
        user = User.objects.get(telegram_id=telegram_id)
    except User.DoesNotExist:
        return {
            "can_create_hackathon": False,
            "is_organizer": False,
            "organized_count": 0,
        }
    organized_count = user.organized_hackathons.count()
    return {
        "can_create_hackathon": can_create_hackathon_for_user(user),
        "is_organizer": organized_count > 0,
        "organized_count": organized_count,
    }


def create_hackathon_by_user(
    *,
    telegram_id,
    name,
    description="",
    schedule_sheet_url="",
    is_team_join_open=True,
):
    telegram_id = require_positive_int(telegram_id, "telegram_id")
    name = require_not_blank(name, "name", max_length=255)
    user = get_profile(telegram_id=telegram_id)

    if not can_create_hackathon_for_user(user):
        raise ServiceError("You cannot create hackathons.", status.HTTP_403_FORBIDDEN)

    description = (description or "").strip()
    schedule_sheet_url = (schedule_sheet_url or "").strip()
    if schedule_sheet_url:
        try:
            URLValidator()(schedule_sheet_url)
        except DjangoValidationError as exc:
            raise ServiceError("Enter a valid schedule URL.", status.HTTP_400_BAD_REQUEST) from exc

    base = slugify(name)[:60] or "hackathon"
    unique_slug = base
    suffix = 0
    while Hackathon.objects.filter(slug=unique_slug).exists():
        suffix += 1
        unique_slug = f"{base}-{suffix}"[:64]

    with transaction.atomic():
        hackathon = Hackathon.objects.create(
            name=name,
            slug=unique_slug,
            description=description,
            schedule_sheet_url=schedule_sheet_url,
            is_team_join_open=bool(is_team_join_open),
            created_by=user,
        )
        hackathon.organizers.add(user)

    return hackathon