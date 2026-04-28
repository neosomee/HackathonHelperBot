"""
Форматирование карточки профиля для Telegram: разные роли и свободный текст навыков.
"""


def membership_from_teammembers(memberships: list, telegram_id: int) -> dict:
    """Логика как в mini_app/js/utils.js getMembershipInfo."""
    tid = str(telegram_id)
    items = memberships if isinstance(memberships, list) else []

    user_memberships = [
        item
        for item in items
        if str((item.get("user") or {}).get("telegram_id") or "") == tid
    ]

    for item in user_memberships:
        if item.get("status") != "accepted":
            continue
        team = item.get("team") or {}
        cap_tid = str((team.get("captain") or {}).get("telegram_id") or "")
        if cap_tid == tid:
            return {
                "status_text": "Капитан",
                "team_name": team.get("name") or "Без названия",
                "has_accepted_team": True,
                "is_captain": True,
            }

    for item in user_memberships:
        if item.get("status") == "accepted":
            team = item.get("team") or {}
            return {
                "status_text": "В команде",
                "team_name": team.get("name") or "Без названия",
                "has_accepted_team": True,
                "is_captain": False,
            }

    for item in user_memberships:
        if item.get("status") == "pending":
            team = item.get("team") or {}
            return {
                "status_text": "Заявка отправлена",
                "team_name": team.get("name") or "Без названия",
                "has_accepted_team": False,
                "is_captain": False,
            }

    return {
        "status_text": "Не в команде",
        "team_name": "",
        "has_accepted_team": False,
        "is_captain": False,
    }


def compose_status_line(user: dict, m: dict, is_organizer: bool) -> str:
    if m["has_accepted_team"]:
        base = m["status_text"]
    elif m["status_text"] == "Заявка отправлена":
        base = "Заявка отправлена"
    elif user.get("role") == "CAPTAIN" or user.get("is_kaptain"):
        base = "Капитан · команда не создана"
    else:
        base = m["status_text"]

    parts = [base]
    if is_organizer:
        parts.append("организатор")
    return " · ".join(parts)


def format_skills_block(skills: str) -> str:
    """Навыки: сохраняем структуру человека, при необходимости добавляем маркеры."""
    raw = (skills or "").strip()
    header = "📌 Навыки:"
    if not raw:
        return f"{header}\n— не указаны"

    if "\n" in raw:
        chunks: list[str] = [header, ""]
        paragraphs = [p.strip() for p in raw.split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [raw]

        for p in paragraphs:
            plines = [ln.strip() for ln in p.split("\n") if ln.strip()]
            for i, ln in enumerate(plines):
                if ln.startswith("🔹"):
                    chunks.append(ln)
                elif ln.startswith("•"):
                    chunks.append(f"• {ln[1:].strip()}")
                elif ln.startswith("* "):
                    chunks.append(f"• {ln[2:].strip()}")
                elif ln.startswith("*"):
                    chunks.append(f"• {ln[1:].strip()}")
                elif ln.startswith(("- ", "– ")):
                    chunks.append(f"• {ln[2:].strip()}")
                elif i == 0 and len(plines) > 1:
                    chunks.append(f"🔹 {ln}")
                else:
                    chunks.append(f"• {ln}")
            chunks.append("")
        return "\n".join(chunks).rstrip()

    if "," in raw and len(raw) < 500:
        bits = [p.strip() for p in raw.split(",") if p.strip()]
        if len(bits) >= 2:
            body = "\n".join(f"• {b}" for b in bits)
            return f"{header}\n\n{body}"

    return f"{header}\n\n{raw}"


def build_profile_card_text(user: dict, m: dict, is_organizer: bool) -> str:
    name = (user.get("full_name") or "—").strip() or "—"
    email = (user.get("email") or "").strip() or "—"
    status = compose_status_line(user, m, is_organizer)

    team = (m.get("team_name") or "").strip()
    if m["status_text"] == "Заявка отправлена" and team:
        team_line = f"{team} (заявка)"
    elif team:
        team_line = team
    else:
        team_line = "—"

    skills_block = format_skills_block(user.get("skills") or "")

    return "\n\n".join(
        [
            f"👤 ФИО: {name}",
            f"✉️ Email: {email}",
            f"👤 Статус: {status}",
            f"👥 Команда: {team_line}",
            skills_block,
        ]
    )
