const tg = window.Telegram?.WebApp;
const apiBaseUrl = window.location.origin;

let currentTelegramId = null;

const screens = {
  home: document.getElementById("home-screen"),
  profile: document.getElementById("profile-screen"),
  teams: document.getElementById("teams-screen"),
};

const profileContent = document.getElementById("profile-content");
const teamsList = document.getElementById("teams-list");
const messageBox = document.getElementById("message");

function getTelegramId() {
  const fromTelegram = tg?.initDataUnsafe?.user?.id;
  if (fromTelegram) {
    return fromTelegram;
  }

  const params = new URLSearchParams(window.location.search);
  return params.get("telegram_id");
}

function showScreen(screenId) {
  Object.values(screens).forEach((screen) => screen.classList.remove("active"));
  document.getElementById(screenId).classList.add("active");
  clearMessage();
}

function showMessage(text, isError = false) {
  messageBox.textContent = text;
  messageBox.classList.toggle("error", isError);
  messageBox.classList.remove("hidden");
}

function clearMessage() {
  messageBox.textContent = "";
  messageBox.classList.add("hidden");
  messageBox.classList.remove("error");
}

async function request(path, options = {}) {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    headers: {
      "Content-Type": "application/json",
    },
    ...options,
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(getErrorMessage(data));
  }

  return data;
}

function getErrorMessage(data) {
  if (data.error) {
    return data.error;
  }

  if (data.errors) {
    return "Проверьте данные и попробуйте снова.";
  }

  return "Не удалось выполнить запрос.";
}

async function loadProfile() {
  showScreen("profile-screen");

  if (!currentTelegramId) {
    profileContent.textContent = "Откройте Mini App из Telegram, чтобы увидеть профиль.";
    return;
  }

  profileContent.textContent = "Загрузка профиля...";

  try {
    const data = await request(`/api/profile/${currentTelegramId}/`);
    const user = data.user;

    profileContent.innerHTML = `
      <div class="profile-row">
        <span class="profile-label">ФИО</span>
        <strong>${escapeHtml(user.full_name)}</strong>
      </div>
      <div class="profile-row">
        <span class="profile-label">Email</span>
        <strong>${escapeHtml(user.email)}</strong>
      </div>
      <div class="profile-row">
        <span class="profile-label">Навыки</span>
        <strong>${escapeHtml(user.skills)}</strong>
      </div>
    `;
  } catch (error) {
    profileContent.textContent = error.message;
  }
}

async function loadTeams() {
  showScreen("teams-screen");
  teamsList.innerHTML = '<div class="panel muted">Загрузка команд...</div>';

  try {
    const data = await request("/api/team/list/");
    renderTeams(data.teams || []);
  } catch (error) {
    teamsList.innerHTML = "";
    showMessage(error.message, true);
  }
}

function renderTeams(teams) {
  if (!teams.length) {
    teamsList.innerHTML = '<div class="panel muted">Пока нет открытых команд.</div>';
    return;
  }

  teamsList.innerHTML = teams.map((team) => `
    <article class="team-card">
      <h3>${escapeHtml(team.name)}</h3>
      <p class="muted">${escapeHtml(team.description)}</p>
      <div class="team-meta">
        <div class="team-field"><strong>Стек:</strong> ${escapeHtml(team.tech_stack)}</div>
        <div class="team-field"><strong>Вакансии:</strong> ${escapeHtml(team.vacancies)}</div>
        <div><span class="status">${team.is_open ? "Набор открыт" : "Набор закрыт"}</span></div>
      </div>
      <button class="button primary" type="button" data-team-id="${team.id}">
        Откликнуться
      </button>
    </article>
  `).join("");

  document.querySelectorAll("[data-team-id]").forEach((button) => {
    button.addEventListener("click", () => applyToTeam(button));
  });
}

async function applyToTeam(button) {
  if (!currentTelegramId) {
    showMessage("Откройте Mini App из Telegram, чтобы отправить отклик.", true);
    return;
  }

  const teamId = Number(button.dataset.teamId);
  button.disabled = true;
  button.textContent = "Отправляем...";

  try {
    await request("/api/team/apply/", {
      method: "POST",
      body: JSON.stringify({
        user_telegram_id: Number(currentTelegramId),
        team_id: teamId,
      }),
    });
    button.textContent = "Заявка отправлена";
    showMessage("Заявка отправлена капитану команды.");
  } catch (error) {
    button.disabled = false;
    button.textContent = "Откликнуться";
    showMessage(mapApplicationError(error.message), true);
  }
}

function mapApplicationError(message) {
  if (message.includes("already in a team")) {
    return "Вы уже состоите в команде.";
  }

  if (message.includes("Application already exists")) {
    return "Вы уже отправили заявку в эту команду.";
  }

  if (message.includes("Team is closed")) {
    return "Команда уже закрыла набор.";
  }

  return message;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

document.getElementById("profile-button").addEventListener("click", loadProfile);
document.getElementById("teams-button").addEventListener("click", loadTeams);

document.querySelectorAll("[data-screen]").forEach((button) => {
  button.addEventListener("click", () => showScreen(button.dataset.screen));
});

if (tg) {
  tg.ready();
  tg.expand();
}

currentTelegramId = getTelegramId();
