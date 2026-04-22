from rest_framework import serializers

from .models import Team, TeamMember, User


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
            "is_active",
            "created_at",
        )
        read_only_fields = ("id", "created_at")


class TeamSerializer(serializers.ModelSerializer):
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
            "created_at",
        )
        read_only_fields = ("id", "created_at")


class TeamMemberSerializer(serializers.ModelSerializer):
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
