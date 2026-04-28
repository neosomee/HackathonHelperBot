from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)

from bot.keyboards.main_menu import main_menu_for_user
from bot.services.api import BackendAPIError
from bot.states.registration import RegistrationState

router = Router()

DIRECTION_LABELS = {
    "backend": "Backend",
    "frontend": "Frontend",
    "qa": "QA",
    "project_manager": "Project Manager",
    "design": "Design",
    "marketing": "Marketing",
    "management": "Management",
    "data_science": "Data Science",
    "mobile_development": "Mobile Development",
    "full_stack": "Full Stack",
    "software_engineer": "Software Engineer",
}

DIRECTION_SKILLS = {
    "backend": {
        1: ["Python", "Java", "Go", "Node.js", "PHP"],
        2: [
            "Django",
            "FastAPI",
            "Flask",
            "Express",
            "Spring",
            "PostgreSQL",
            "Redis",
            "Docker",
            "REST API",
            "GraphQL",
        ],
    },
    "frontend": {
        1: ["HTML", "CSS", "JavaScript", "TypeScript"],
        2: ["React", "Vue", "Angular", "Next.js", "Tailwind", "Redux"],
    },
    "qa": {
        1: ["Manual Testing", "Automation Testing", "API Testing"],
        2: ["Selenium", "Cypress", "Postman", "Playwright", "Test Cases"],
    },
    "project_manager": {
        1: ["Agile", "Scrum", "Kanban"],
        2: ["Jira", "Notion", "Risk Management", "Team Leadership"],
    },
    "design": {
        1: ["UI/UX", "Wireframing", "Prototyping"],
        2: ["Figma", "Adobe XD", "Photoshop", "Illustrator", "Sketch"],
    },
    "marketing": {
        1: ["SEO", "SMM", "Content Marketing"],
        2: ["Google Ads", "Analytics", "Copywriting", "Email Marketing"],
    },
    "management": {
        1: ["Team Management", "Communication"],
        2: ["Business Strategy", "Planning", "Negotiation"],
    },
    "data_science": {
        1: ["Python", "Pandas", "NumPy"],
        2: ["Machine Learning", "TensorFlow", "PyTorch", "Data Analysis", "Statistics"],
    },
    "mobile_development": {
        1: ["Swift", "Kotlin"],
        2: ["Flutter", "React Native", "Android", "iOS"],
    },
    "full_stack": {
        1: ["Python", "JavaScript", "TypeScript"],
        2: ["Django", "React", "PostgreSQL", "Docker", "REST API"],
    },
    "software_engineer": {
        1: ["Algorithms", "Data Structures"],
        2: ["System Design", "OOP", "Git", "Testing"],
    },
}


def skill_slug(skill: str) -> str:
    return (
        skill.lower()
        .replace("/", "_")
        .replace(".", "")
        .replace(" ", "_")
        .replace("-", "_")
    )


def skill_by_slug(direction: str, slug: str) -> str | None:
    for skills in DIRECTION_SKILLS.get(direction, {}).values():
        for skill in skills:
            if skill_slug(skill) == slug:
                return skill
    return None


def role_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="👤 Участник"),
                KeyboardButton(text="👑 Капитан"),
            ],
            [
                KeyboardButton(text="📋 Организатор"),
                KeyboardButton(text="👑 Капитан + организатор"),
            ],
        ],
        resize_keyboard=True,
    )


def direction_keyboard(selected_directions: list[str] | None = None) -> InlineKeyboardMarkup:
    selected_directions = selected_directions or []
    rows = []
    buttons = []

    for slug, label in DIRECTION_LABELS.items():
        prefix = "✅ " if slug in selected_directions else ""
        buttons.append(
            InlineKeyboardButton(
                text=f"{prefix}{label}",
                callback_data=f"direction:{slug}",
            )
        )

    for index in range(0, len(buttons), 2):
        rows.append(buttons[index : index + 2])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def skills_keyboard(direction: str, selected_skills: list[str], current_page: int) -> InlineKeyboardMarkup:
    rows = []
    buttons = []

    page_skills = DIRECTION_SKILLS[direction][current_page]
    for skill in page_skills:
        prefix = "✅ " if skill in selected_skills else ""
        buttons.append(
            InlineKeyboardButton(
                text=f"{prefix}{skill}",
                callback_data=f"skill:{skill_slug(skill)}",
            )
        )

    for index in range(0, len(buttons), 3):
        rows.append(buttons[index : index + 3])

    if current_page == 1:
        rows.append(
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data="back:direction"),
                InlineKeyboardButton(text="➡️ Далее", callback_data="page:next"),
            ]
        )
    else:
        rows.append(
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data="back:page1"),
                InlineKeyboardButton(text="➡️ Далее", callback_data="page:next"),
            ]
        )

    rows.append(
        [InlineKeyboardButton(text="➕ Добавить направление", callback_data="add_direction")]
    )
    rows.append([InlineKeyboardButton(text="✅ Завершить", callback_data="finish")])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_skills_string(selected_directions: list[str], selected_skills: dict[str, list[str]]) -> str:
    parts = []
    for direction in selected_directions:
        skills = selected_skills.get(direction, [])
        if skills:
            parts.append(f"{DIRECTION_LABELS[direction]}: {', '.join(skills)}")
    return " | ".join(parts)


@router.message(RegistrationState.full_name)
async def process_full_name(message: Message, state: FSMContext):
    full_name = (message.text or "").strip()
    if not full_name:
        await message.answer("ФИО не может быть пустым. Введите ваше ФИО:")
        return

    await state.update_data(full_name=full_name)
    await state.set_state(RegistrationState.email)
    await message.answer("Введите email:")


@router.message(RegistrationState.email)
async def process_email(message: Message, state: FSMContext):
    email = (message.text or "").strip()
    if not email:
        await message.answer("Email не может быть пустым. Введите email:")
        return

    await state.update_data(email=email)
    await state.set_state(RegistrationState.skills)
    await message.answer(
        "Укажите ваше направление:",
        reply_markup=direction_keyboard(),
    )


@router.callback_query(RegistrationState.skills, F.data.startswith("direction:"))
async def process_direction(callback: CallbackQuery, state: FSMContext):
    direction = callback.data.split(":", 1)[1]
    if direction not in DIRECTION_SKILLS:
        await callback.answer("Направление не найдено.", show_alert=True)
        return

    data = await state.get_data()
    selected_directions = data.get("selected_directions", [])
    selected_skills = data.get("selected_skills", {})

    if direction not in selected_directions:
        selected_directions.append(direction)
    selected_skills.setdefault(direction, [])

    await state.update_data(
        current_direction=direction,
        selected_directions=selected_directions,
        selected_skills=selected_skills,
        current_page=1,
    )

    await callback.message.edit_text(
        f"Выберите навыки: {DIRECTION_LABELS[direction]}",
        reply_markup=skills_keyboard(direction, selected_skills[direction], 1),
    )
    await callback.answer()


@router.callback_query(RegistrationState.skills, F.data.startswith("skill:"))
async def toggle_skill(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    direction = data.get("current_direction")
    current_page = data.get("current_page", 1)

    if not direction:
        await callback.answer("Сначала выберите направление.", show_alert=True)
        return

    slug = callback.data.split(":", 1)[1]
    skill = skill_by_slug(direction, slug)
    if not skill:
        await callback.answer("Навык не найден.", show_alert=True)
        return

    selected_skills = data.get("selected_skills", {})
    direction_skills = selected_skills.get(direction, [])

    if skill in direction_skills:
        direction_skills.remove(skill)
    else:
        direction_skills.append(skill)

    selected_skills[direction] = direction_skills
    await state.update_data(selected_skills=selected_skills)

    await callback.message.edit_reply_markup(
        reply_markup=skills_keyboard(direction, direction_skills, current_page)
    )
    await callback.answer()


@router.callback_query(RegistrationState.skills, F.data == "page:next")
async def process_next_skill_page(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    direction = data.get("current_direction")
    selected_skills = data.get("selected_skills", {})
    current_page = data.get("current_page", 1)

    if not direction:
        await callback.answer("Сначала выберите направление.", show_alert=True)
        return

    next_page = 2 if current_page == 1 else 2
    await state.update_data(current_page=next_page)

    await callback.message.edit_text(
        f"Выберите навыки: {DIRECTION_LABELS[direction]}",
        reply_markup=skills_keyboard(direction, selected_skills.get(direction, []), next_page),
    )
    await callback.answer()


@router.callback_query(RegistrationState.skills, F.data == "back:direction")
async def back_to_direction(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected_directions = data.get("selected_directions", [])

    await state.update_data(current_direction=None, current_page=1)
    await callback.message.edit_text(
        "Укажите ваше направление:",
        reply_markup=direction_keyboard(selected_directions),
    )
    await callback.answer()


@router.callback_query(RegistrationState.skills, F.data == "back:page1")
async def back_to_page_one(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    direction = data.get("current_direction")
    selected_skills = data.get("selected_skills", {})

    if not direction:
        await callback.answer("Сначала выберите направление.", show_alert=True)
        return

    await state.update_data(current_page=1)
    await callback.message.edit_text(
        f"Выберите навыки: {DIRECTION_LABELS[direction]}",
        reply_markup=skills_keyboard(direction, selected_skills.get(direction, []), 1),
    )
    await callback.answer()


@router.callback_query(RegistrationState.skills, F.data == "add_direction")
async def add_direction(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected_directions = data.get("selected_directions", [])

    await state.update_data(current_direction=None, current_page=1)
    await callback.message.edit_text(
        "Укажите ваше направление:",
        reply_markup=direction_keyboard(selected_directions),
    )
    await callback.answer()


@router.callback_query(RegistrationState.skills, F.data == "finish")
async def finish_skills_selection(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected_directions = data.get("selected_directions", [])
    selected_skills = data.get("selected_skills", {})
    skills = build_skills_string(selected_directions, selected_skills)

    if not skills:
        await callback.answer("Выберите хотя бы один навык.", show_alert=True)
        return

    await state.update_data(skills=skills)
    await state.set_state(RegistrationState.role)

    await callback.message.edit_text("Навыки сохранены.")
    await callback.message.answer(
        "Выберите роль:",
        reply_markup=role_keyboard(),
    )
    await callback.answer()


@router.message(RegistrationState.role)
async def process_role(message: Message, state: FSMContext, api):
    text = (message.text or "").lower()

    is_kaptain = False
    can_create_hackathons = False

    if "капитан" in text and "организатор" in text:
        is_kaptain = True
        can_create_hackathons = True
    elif "организатор" in text:
        can_create_hackathons = True
    elif "капитан" in text:
        is_kaptain = True
    elif "участник" in text:
        pass
    else:
        await message.answer("Пожалуйста, выберите одну из кнопок.")
        return

    data = await state.get_data()
    telegram_id = message.from_user.id

    try:
        await api.register_user(
            telegram_id=telegram_id,
            full_name=data["full_name"],
            email=data["email"],
            skills=data["skills"],
            is_kaptain=is_kaptain,
            can_create_hackathons=can_create_hackathons,
        )
    except BackendAPIError as exc:
        await message.answer(f"Ошибка регистрации: {exc.message}")
        return

    await state.clear()

    menu_markup = await main_menu_for_user(api, telegram_id)
    extra = ""
    if can_create_hackathons:
        extra = "\n\nВы можете создавать хакатоны (Mini App / бот «➕ Новый хакатон»)."

    await message.answer(
        "Вы успешно зарегистрированы." + extra,
        reply_markup=menu_markup,
    )