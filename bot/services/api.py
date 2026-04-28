import aiohttp


class BackendAPIError(Exception):
    def __init__(self, message, status):
        self.message = message
        self.status = status
        super().__init__(message)


class BackendAPI:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")
        self.session: aiohttp.ClientSession | None = None

    async def init(self):
        """Создаём одну HTTP-сессию (важно для производительности)."""
        if not self.session:
            self.session = aiohttp.ClientSession()

    async def close(self):
        if self.session:
            await self.session.close()

    async def _request(self, method, path, json=None):
        if not self.session:
            raise RuntimeError("API session not initialized. Call api.init()")

        url = f"{self.base_url}{path}"

        async with self.session.request(method, url, json=json) as response:
            data = await self._read_json(response)

            if response.status >= 400:
                raise BackendAPIError(
                    self._get_error_message(data),
                    response.status,
                )

            return data

    async def _read_json(self, response):
        try:
            return await response.json()
        except aiohttp.ContentTypeError:
            return {}

    def _get_error_message(self, data):
        if isinstance(data, dict):
            if "error" in data:
                return data["error"]
            if "errors" in data:
                return str(data["errors"])
        return "Backend API request failed."

    # ---------------- USERS ----------------

    async def get_profile(self, telegram_id):
        return await self._request("GET", f"/api/profile/{telegram_id}/")

    async def register_user(
        self,
        telegram_id,
        full_name,
        email,
        skills,
        is_kaptain=False,
        can_create_hackathons=False,
    ):
        return await self._request(
            "POST",
            "/api/register/",
            json={
                "telegram_id": telegram_id,
                "full_name": full_name,
                "email": email,
                "skills": skills,
                "is_kaptain": is_kaptain,
                "can_create_hackathons": can_create_hackathons,
            },
        )

    # ---------------- TEAMS ----------------

    async def get_team_members(self):
        return await self._request("GET", "/api/team-members/")

    async def create_team(
        self,
        captain_telegram_id,
        name,
        description,
        tech_stack,
        vacancies,
    ):
        return await self._request(
            "POST",
            "/api/team/create/",
            json={
                "captain_telegram_id": captain_telegram_id,
                "name": name,
                "description": description,
                "tech_stack": tech_stack,
                "vacancies": vacancies,
            },
        )

    # ---------------- HACKATHONS ----------------

    async def get_hackathon_permissions(self, telegram_id):
        return await self._request(
            "GET",
            f"/api/hackathons/permissions/?telegram_id={telegram_id}",
        )

    async def create_hackathon(
        self,
        telegram_id,
        name,
        description="",
        schedule_sheet_url="",
        is_team_join_open=True,
    ):
        return await self._request(
            "POST",
            "/api/hackathons/create/",
            json={
                "telegram_id": telegram_id,
                "name": name,
                "description": description,
                "schedule_sheet_url": schedule_sheet_url,
                "is_team_join_open": is_team_join_open,
            },
        )

    async def get_organized_hackathons(self, telegram_id):
        return await self._request(
            "GET",
            f"/api/hackathons/organized/?telegram_id={telegram_id}",
        )

    async def list_my_schedule_hackathons(self, telegram_id):
        return await self._request(
            "GET",
            f"/api/hackathons/my-schedule/?telegram_id={telegram_id}",
        )

    async def get_hackathon_schedule_status(self, hackathon_id, telegram_id):
        return await self._request(
            "GET",
            f"/api/hackathons/{hackathon_id}/schedule/status/?telegram_id={telegram_id}",
        )

    # ---------------- EXPORT ----------------

    async def download_hackathon_export(self, hackathon_id, telegram_id, kind):
        if not self.session:
            raise RuntimeError("API session not initialized. Call api.init()")

        url = (
            f"{self.base_url}/api/hackathons/{hackathon_id}/export/"
            f"?telegram_id={telegram_id}&kind={kind}"
        )

        async with self.session.get(url) as response:
            body = await response.read()

            if response.status >= 400:
                text = body.decode("utf-8", errors="replace").strip()
                raise BackendAPIError(text or "Export failed.", response.status)

            return body