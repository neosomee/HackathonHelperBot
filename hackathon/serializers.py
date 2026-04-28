from rest_framework import serializers

from .models import Hackathon, Team, TeamMember, User


FIELD_ERROR_MESSAGES = {
    "required": "This field is required.",
    "blank": "This field cannot be empty.",
    "invalid": "Invalid value.",
}


class PositiveIntegerField(serializers.IntegerField):
    default_error_messages = {
        **FIELD_ERROR_MESSAGES,
        "min_value": "This value must be greater than zero.",
    }

    def __init__(self, **kwargs):
        kwargs.setdefault("min_value", 1)
        super().__init__(**kwargs)


class NonBlankCharField(serializers.CharField):
    default_error_messages = {
        **FIELD_ERROR_MESSAGES,
        "max_length": "This field is too long.",
    }

    def __init__(self, **kwargs):
        kwargs.setdefault("allow_blank", False)
        kwargs.setdefault("trim_whitespace", True)
        super().__init__(**kwargs)


class NonBlankEmailField(serializers.EmailField):
    default_error_messages = {
        **FIELD_ERROR_MESSAGES,
        "invalid": "Enter a valid email address.",
    }

    def __init__(self, **kwargs):
        kwargs.setdefault("allow_blank", False)
        kwargs.setdefault("trim_whitespace", True)
        super().__init__(**kwargs)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "telegram_id",
            "full_name",
            "email",
            "skills",
            "role",
            "is_kaptain",
            "can_create_hackathons",
            "is_active",
            "created_at",
        )
        read_only_fields = ("id", "created_at")


class RegisterUserSerializer(serializers.Serializer):
    telegram_id = PositiveIntegerField(required=True)
    full_name = NonBlankCharField(required=True, max_length=255)
    email = NonBlankEmailField(required=True)
    skills = NonBlankCharField(required=True)
    is_kaptain = serializers.BooleanField(required=False, default=False)
    can_create_hackathons = serializers.BooleanField(required=False, default=False)


class ScheduleSubscribeSerializer(serializers.Serializer):
    telegram_id = PositiveIntegerField(required=True)


class UpdateUserProfileSerializer(serializers.Serializer):
    telegram_id = PositiveIntegerField(required=True)
    full_name = NonBlankCharField(required=False, max_length=255)
    email = NonBlankEmailField(required=False)
    skills = NonBlankCharField(required=False)

    def validate(self, attrs):
        editable_fields = {"full_name", "email", "skills"}
        if not editable_fields.intersection(attrs):
            raise serializers.ValidationError(
                "Provide at least one profile field: full_name, email, or skills."
            )
        return attrs


class TeamSerializer(serializers.ModelSerializer):
    captain = UserSerializer(read_only=True)

    class Meta:
        model = Team
        fields = (
            "id",
            "name",
            "description",
            "captain",
            "tech_stack",
            "vacancies",
            "is_open",
            "max_members",
            "created_at",
        )
        read_only_fields = ("id", "created_at")


class CreateTeamSerializer(serializers.Serializer):
    captain_telegram_id = PositiveIntegerField(required=True)
    name = NonBlankCharField(required=True, max_length=255)
    description = NonBlankCharField(required=True)
    tech_stack = NonBlankCharField(required=True)
    vacancies = NonBlankCharField(required=True)
    max_members = serializers.IntegerField(required=False, min_value=1, max_value=100)


class ApplyToTeamSerializer(serializers.Serializer):
    user_telegram_id = PositiveIntegerField(required=True)
    team_id = PositiveIntegerField(required=True)


class TeamDecisionSerializer(serializers.Serializer):
    captain_telegram_id = PositiveIntegerField(required=True)
    user_telegram_id = PositiveIntegerField(required=True)
    team_id = PositiveIntegerField(required=True)
    decision = serializers.ChoiceField(choices=("accept", "reject"))


class TeamSettingsSerializer(serializers.Serializer):
    captain_telegram_id = PositiveIntegerField(required=True)
    team_id = PositiveIntegerField(required=True)

    name = NonBlankCharField(required=False, max_length=255)
    description = NonBlankCharField(required=False)
    tech_stack = NonBlankCharField(required=False)
    vacancies = NonBlankCharField(required=False)

    is_open = serializers.BooleanField(required=False)
    max_members = serializers.IntegerField(required=False, min_value=1, max_value=100)


class CreateHackathonSerializer(serializers.Serializer):
    telegram_id = PositiveIntegerField(required=True)
    name = NonBlankCharField(required=True, max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    schedule_sheet_url = serializers.URLField(required=False, allow_blank=True, default="")
    is_team_join_open = serializers.BooleanField(required=False, default=True)


class HackathonReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hackathon
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "schedule_sheet_url",
            "is_team_join_open",
            "created_at",
        )
        read_only_fields = (
            "id",
            "name",
            "slug",
            "description",
            "schedule_sheet_url",
            "is_team_join_open",
            "created_at",
        )


class JoinHackathonSerializer(serializers.Serializer):
    captain_telegram_id = PositiveIntegerField(required=True)


class LeaveTeamSerializer(serializers.Serializer):
    user_telegram_id = PositiveIntegerField(required=True)


class TransferCaptainSerializer(serializers.Serializer):
    captain_telegram_id = PositiveIntegerField(required=True)
    team_id = PositiveIntegerField(required=True)
    new_captain_telegram_id = PositiveIntegerField(required=True)


class DeleteTeamSerializer(serializers.Serializer):
    captain_telegram_id = PositiveIntegerField(required=True)
    team_id = PositiveIntegerField(required=True)


class DeleteProfileSerializer(serializers.Serializer):
    telegram_id = PositiveIntegerField(required=True)


class TeamMemberSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    team = TeamSerializer(read_only=True)

    class Meta:
        model = TeamMember
        fields = (
            "id",
            "user",
            "team",
            "status",
            "created_at",
        )
        read_only_fields = ("id", "created_at")