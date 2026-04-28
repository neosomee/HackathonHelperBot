from django.db import models


class User(models.Model):
    class Role(models.TextChoices):
        PARTICIPANT = "PARTICIPANT", "Participant"
        CAPTAIN = "CAPTAIN", "Captain"

    telegram_id = models.BigIntegerField(unique=True)
    full_name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    skills = models.TextField(blank=True)

    role = models.CharField(
        max_length=32,
        choices=Role.choices,
        default=Role.PARTICIPANT,
    )

    is_kaptain = models.BooleanField(
        default=False,
        help_text="Auto-synced with role=CAPTAIN",
    )

    can_create_hackathons = models.BooleanField(
        default=False,
        help_text="Может создавать хакатоны (выбор при регистрации или назначение в админке).",
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("full_name",)

    def save(self, *args, **kwargs):
        self.is_kaptain = self.role == self.Role.CAPTAIN
        super().save(*args, **kwargs)

    def __str__(self):
        return self.full_name


class Team(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    captain = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="captained_teams",
    )

    tech_stack = models.TextField(blank=True)
    vacancies = models.TextField(blank=True)

    is_open = models.BooleanField(default=True)

    max_members = models.PositiveSmallIntegerField(default=5)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name


class TeamMember(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=Status.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "team"], name="uniq_user_team")
        ]

    def __str__(self):
        return f"{self.user} -> {self.team} ({self.status})"


class Hackathon(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=64, unique=True)
    description = models.TextField(blank=True)
    schedule_sheet_url = models.URLField(
        max_length=500,
        blank=True,
        help_text="Ссылка на Google Таблицу с расписанием (опционально).",
    )
    is_team_join_open = models.BooleanField(
        default=True,
        help_text="Капитаны могут подключать команды к этому хакатону.",
    )
    organizers = models.ManyToManyField(
        User,
        related_name="organized_hackathons",
        blank=True,
        help_text="Права организатора только через эту связь (вариант A).",
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_hackathons",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return self.name


class HackathonTeam(models.Model):
    hackathon = models.ForeignKey(
        Hackathon,
        on_delete=models.CASCADE,
        related_name="hackathon_teams",
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name="hackathon_links",
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["hackathon", "team"],
                name="uniq_hackathon_team",
            ),
        ]
        ordering = ("-joined_at",)

    def __str__(self):
        return f"{self.team.name} @ {self.hackathon.name}"


class HackathonScheduleSubscription(models.Model):
    """Подписка пользователя на напоминания по строкам расписания из Google Таблицы хакатона."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="schedule_subscriptions")
    hackathon = models.ForeignKey(
        Hackathon,
        on_delete=models.CASCADE,
        related_name="schedule_subscriptions",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "hackathon"],
                name="uniq_user_hackathon_schedule_subscription",
            ),
        ]
        ordering = ("-updated_at",)

    def __str__(self):
        return f"{self.user} → {self.hackathon} (active={self.is_active})"


class ScheduleNotificationLog(models.Model):
    """Чтобы не слать одно и то же напоминание повторно."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="schedule_notification_logs")
    hackathon = models.ForeignKey(
        Hackathon,
        on_delete=models.CASCADE,
        related_name="schedule_notification_logs",
    )
    dedupe_key = models.CharField(max_length=128, db_index=True)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "dedupe_key"],
                name="uniq_schedule_notify_dedupe",
            ),
        ]
        ordering = ("-sent_at",)