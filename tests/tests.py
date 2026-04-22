from django.test import TestCase
from rest_framework import status

from hackathon.models import TeamMember, User
from hackathon.services import (
    ServiceError,
    apply_to_team,
    create_team,
    decide_team_request,
    register_user,
)


class HackathonServiceTests(TestCase):
    def create_user(self, telegram_id, full_name="Test User"):
        user, created = register_user(
            telegram_id=telegram_id,
            full_name=full_name,
            email=f"user{telegram_id}@example.com",
            skills="Python, Django",
        )
        self.assertTrue(created)
        return user

    def create_team_with_captain(self):
        captain = self.create_user(1001, "Captain User")
        team = create_team(
            captain_telegram_id=captain.telegram_id,
            name="Demo Team",
            description="Team for demo",
            tech_stack="Django, PostgreSQL",
            vacancies="Frontend developer",
        )
        return captain, team

    def test_register_user(self):
        user = self.create_user(1000, "Participant User")

        self.assertEqual(user.full_name, "Participant User")
        self.assertEqual(user.role, User.Role.PARTICIPANT)
        self.assertTrue(user.is_active)

    def test_create_team_adds_captain_as_accepted_member(self):
        captain, team = self.create_team_with_captain()
        captain.refresh_from_db()

        self.assertEqual(team.captain, captain)
        self.assertEqual(captain.role, User.Role.CAPTAIN)
        self.assertTrue(
            TeamMember.objects.filter(
                user=captain,
                team=team,
                status=TeamMember.Status.ACCEPTED,
            ).exists()
        )

    def test_apply_to_team_creates_pending_request(self):
        _, team = self.create_team_with_captain()
        user = self.create_user(1002, "Applicant User")

        application = apply_to_team(
            user_telegram_id=user.telegram_id,
            team_id=team.id,
        )

        self.assertEqual(application.status, TeamMember.Status.PENDING)
        self.assertEqual(application.user, user)
        self.assertEqual(application.team, team)

    def test_captain_accepts_request(self):
        captain, team = self.create_team_with_captain()
        user = self.create_user(1003, "Accepted User")
        apply_to_team(user_telegram_id=user.telegram_id, team_id=team.id)

        application = decide_team_request(
            captain_telegram_id=captain.telegram_id,
            user_telegram_id=user.telegram_id,
            team_id=team.id,
            decision="accept",
        )

        self.assertEqual(application.status, TeamMember.Status.ACCEPTED)

    def test_captain_rejects_request(self):
        captain, team = self.create_team_with_captain()
        user = self.create_user(1004, "Rejected User")
        apply_to_team(user_telegram_id=user.telegram_id, team_id=team.id)

        application = decide_team_request(
            captain_telegram_id=captain.telegram_id,
            user_telegram_id=user.telegram_id,
            team_id=team.id,
            decision="reject",
        )

        self.assertEqual(application.status, TeamMember.Status.REJECTED)

    def test_user_cannot_apply_to_same_team_twice(self):
        _, team = self.create_team_with_captain()
        user = self.create_user(1005, "Duplicate Applicant")
        apply_to_team(user_telegram_id=user.telegram_id, team_id=team.id)

        with self.assertRaises(ServiceError) as context:
            apply_to_team(user_telegram_id=user.telegram_id, team_id=team.id)

        self.assertEqual(context.exception.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(context.exception.message, "Application already exists.")

    def test_user_in_team_cannot_create_team(self):
        captain, team = self.create_team_with_captain()
        user = self.create_user(1006, "Team Member")
        apply_to_team(user_telegram_id=user.telegram_id, team_id=team.id)
        decide_team_request(
            captain_telegram_id=captain.telegram_id,
            user_telegram_id=user.telegram_id,
            team_id=team.id,
            decision="accept",
        )

        with self.assertRaises(ServiceError) as context:
            create_team(
                captain_telegram_id=user.telegram_id,
                name="Another Team",
                description="Should not be created",
                tech_stack="Django",
                vacancies="Designer",
            )

        self.assertEqual(context.exception.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(context.exception.message, "User is already in a team.")

    def test_non_captain_cannot_process_request(self):
        _, team = self.create_team_with_captain()
        user = self.create_user(1007, "Applicant")
        other_user = self.create_user(1008, "Not Captain")
        apply_to_team(user_telegram_id=user.telegram_id, team_id=team.id)

        with self.assertRaises(ServiceError) as context:
            decide_team_request(
                captain_telegram_id=other_user.telegram_id,
                user_telegram_id=user.telegram_id,
                team_id=team.id,
                decision="accept",
            )

        self.assertEqual(context.exception.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            context.exception.message,
            "Only the team captain can process this request.",
        )
