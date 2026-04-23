import aiohttp


class BackendAPIError(Exception):
    def __init__(self, message, status):
        self.message = message
        self.status = status
        super().__init__(message)


class BackendAPI:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")

    async def _request(self, method, path, json=None):
        url = f"{self.base_url}{path}"
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, json=json) as response:
                data = await self._read_json(response)
                if response.status >= 400:
                    raise BackendAPIError(self._get_error_message(data), response.status)
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

    async def get_profile(self, telegram_id):
        return await self._request("GET", f"/api/profile/{telegram_id}/")

    async def register_user(self, telegram_id, full_name, email, skills):
        payload = {
            "telegram_id": telegram_id,
            "full_name": full_name,
            "email": email,
            "skills": skills,
        }
        return await self._request("POST", "/api/register/", json=payload)

    async def create_team(self, captain_telegram_id, name, description, tech_stack, vacancies):
        payload = {
            "captain_telegram_id": captain_telegram_id,
            "name": name,
            "description": description,
            "tech_stack": tech_stack,
            "vacancies": vacancies,
        }
        return await self._request("POST", "/api/team/create/", json=payload)
