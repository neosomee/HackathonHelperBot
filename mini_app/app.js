const tg = window.Telegram?.WebApp;

let currentTelegramId = null;
let allTeams = [];
let profileFlashMessage = null;

const screens = {
  home: document.getElementById("home-screen"),
  profile: document.getElementById("profile-screen"),
  teams: document.getElementById("teams-screen"),
};

const profileContent = document.getElementById("profile-content");
const teamsList = document.getElementById("teams-list");
const messageBox = document.getElementById("message");
const devHint = document.getElementById("dev-hint");
const teamSearchInput = document.getElementById("team-search");
const techStackFilter = document.getElementById("tech-stack-filter");




function getTelegramId() {
  const fromTelegram = tg?.initDataUnsafe?.user?.id;
  if (fromTelegram) {
    return String(fromTelegram);
  }

  const params = new URLSearchParams(window.location.search);
  const fromQuery = params.get("telegram_id");
  if (fromQuery) {
    localStorage.setItem("mini_app_telegram_id", fromQuery);
    return fromQuery;
  }

  const fromStorage = localStorage.getItem("mini_app_telegram_id");
  if (fromStorage) {
    return fromStorage;
  }

  const fromPrompt = window.prompt("Введите Telegram ID для локальной разработки:");
  if (fromPrompt) {
    localStorage.setItem("mini_app_telegram_id", fromPrompt);
    return fromPrompt;
  }

  return null;
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
  try {
    const response = await fetch(path, {
      headers: {
        "Content-Type": "application/json",
      },
      ...options,
    });

    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(getErrorMessage(response.status, data));
    }

    return data;
  } catch (error) {
    if (error instanceof TypeError) {
      throw new Error(
        "Backend API недоступен. Откройте Mini App через http://127.0.0.1:8000/miniapp/."
      );
    }

    throw error;
  }
}

function getErrorMessage(statusCode, data) {
  if (data.error) {
    return data.error;
  }

  if (data.errors) {
    return "Ошибка валидации. Проверьте данные и попробуйте снова.";
  }

  if (statusCode === 404) {
    return "Данные не найдены.";
  }

  if (statusCode >= 500) {
    return "Ошибка сервера. Попробуйте позже.";
  }

  return "Не удалось выполнить запрос.";
}

async function loadProfile() {
  showScreen("profile-screen");

  if (!currentTelegramId) {
    profileContent.textContent =
      "Не удалось определить Telegram ID. Откройте Mini App из Telegram или передайте ?telegram_id=...";
    return;
  }

  profileContent.textContent = "Загрузка профиля...";

  try {
    const profileData = await request(`/api/profile/${currentTelegramId}/`);
    const user = profileData.user;
    let membershipInfo = {
      statusText: "Не удалось определить",
      teamName: "Недоступно",
    };
    let captainPanelHtml = "";
    let createTeamHtml = "";

    try {
      const membershipData = await request("/api/team-members/");
      membershipInfo = getMembershipInfo(membershipData, currentTelegramId);

      if (membershipInfo.isCaptain) {
        captainPanelHtml = await buildCaptainPanel(user, membershipData);
      }

      if (!membershipInfo.hasAcceptedTeam && !membershipInfo.isCaptain) {
        createTeamHtml = buildCreateTeamBlock();
      }
    } catch (error) {
      membershipInfo = {
        statusText: "Не удалось определить",
        teamName: "Недоступно",
        isCaptain: false,
        hasAcceptedTeam: false,
        hasPendingApplication: false,
      };
    }

    profileContent.innerHTML = `
      <div class="profile-card">
        <div class="profile-row">
          <span class="profile-label">ФИО</span>
          <strong class="profile-value">${escapeHtml(user.full_name)}</strong>
        </div>
        <div class="profile-row">
          <span class="profile-label">Email</span>
          <strong class="profile-value">${escapeHtml(user.email)}</strong>
        </div>
        <div class="profile-row">
          <span class="profile-label">Навыки</span>
          <strong class="profile-value">${escapeHtml(user.skills)}</strong>
        </div>
        <div class="profile-row">
          <span class="profile-label">Статус участия</span>
          <strong class="profile-value">${escapeHtml(membershipInfo.statusText)}</strong>
        </div>
        <div class="profile-row">
          <span class="profile-label">Команда</span>
          <strong class="profile-value">${escapeHtml(membershipInfo.teamName)}</strong>
        </div>
        ${createTeamHtml}
        ${captainPanelHtml}
      </div>
    `;

    bindCaptainRequestActions();
    bindCreateTeamActions();
    bindCaptainSettingsActions();
  } catch (error) {
    profileContent.textContent =
      error.message === "User not found."
        ? "Профиль не найден. Сначала зарегистрируйтесь через Telegram-бота."
        : error.message;
  }
}

function getMembershipInfo(membershipData, telegramId) {
  const memberships = Array.isArray(membershipData) ? membershipData : [];

  const userMemberships = memberships.filter((item) => {
    return String(item.user?.telegram_id || "") === String(telegramId);
  });

  const captainMembership = userMemberships.find((item) => {
    return (
      item.status === "accepted" &&
      String(item.team?.captain?.telegram_id || "") === String(telegramId)
    );
  });

  if (captainMembership) {
    return {
      statusText: "Капитан",
      teamName: captainMembership.team?.name || "Без названия",
      isCaptain: true,
      hasAcceptedTeam: true,
      hasPendingApplication: false,
    };
  }

  const acceptedMembership = userMemberships.find((item) => item.status === "accepted");
  if (acceptedMembership) {
    return {
      statusText: "В команде",
      teamName: acceptedMembership.team?.name || "Без названия",
      isCaptain: false,
      hasAcceptedTeam: true,
      hasPendingApplication: false,
    };
  }

  const pendingMembership = userMemberships.find((item) => item.status === "pending");
  if (pendingMembership) {
    return {
      statusText: "Заявка отправлена",
      teamName: pendingMembership.team?.name || "Без названия",
      isCaptain: false,
      hasAcceptedTeam: false,
      hasPendingApplication: true,
    };
  }

  return {
    statusText: "Не участвует в команде",
    teamName: "Нет команды",
    isCaptain: false,
    hasAcceptedTeam: false,
    hasPendingApplication: false,
  };
}

function bindCreateTeamActions() {
  const toggleButton = document.getElementById("create-team-toggle");
  const form = document.getElementById("create-team-form");
  const messageBox = document.getElementById("create-team-message");

  if (!toggleButton || !form || !messageBox) {
    return;
  }

  const setMessage = (text, isError = false) => {
    messageBox.textContent = text;
    messageBox.classList.remove("hidden", "error", "success");
    messageBox.classList.add(isError ? "error" : "success");
  };

  toggleButton.addEventListener("click", () => {
    form.classList.toggle("hidden");
    toggleButton.textContent = form.classList.contains("hidden")
      ? "Открыть форму"
      : "Скрыть форму";
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    if (!currentTelegramId) {
      setMessage("Не удалось определить Telegram ID.", true);
      return;
    }

    const formData = new FormData(form);

    const payload = {
      captain_telegram_id: Number(currentTelegramId),
      name: String(formData.get("name") || "").trim(),
      description: String(formData.get("description") || "").trim(),
      tech_stack: String(formData.get("tech_stack") || "").trim(),
      vacancies: String(formData.get("vacancies") || "").trim(),
    };

    if (!payload.name || !payload.description || !payload.tech_stack || !payload.vacancies) {
      setMessage("Заполните все поля формы.", true);
      return;
    }

    const submitButton = form.querySelector('button[type="submit"]');
    const originalText = submitButton.textContent;

    submitButton.disabled = true;
    submitButton.textContent = "Создаём...";

    try {
      await request("/api/team/create/", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      setMessage("Команда успешно создана.");
      form.reset();
      form.classList.add("hidden");
      toggleButton.textContent = "Открыть форму";

      await loadProfile();
    } catch (error) {
      setMessage(error.message, true);
    } finally {
      submitButton.disabled = false;
      submitButton.textContent = originalText;
    }
  });
}

function bindCaptainSettingsActions() {
  const saveBtn = document.getElementById("team-settings-save");
  const panel = document.querySelector(".captain-panel");
  const toggle = document.getElementById("team-open-toggle");
  const maxInput = document.getElementById("team-max-members");
  const nameInput = document.getElementById("team-name");
  const descriptionInput = document.getElementById("team-description");
  const techStackInput = document.getElementById("team-tech-stack");
  const vacanciesInput = document.getElementById("team-vacancies");

  const teamId = Number(panel?.dataset.teamId);
  if (!saveBtn || !panel || !toggle || !maxInput || !nameInput || !descriptionInput || !techStackInput || !vacanciesInput || !teamId) {
    return;
  }

  saveBtn.addEventListener("click", async () => {
    saveBtn.disabled = true;
    saveBtn.textContent = "Сохраняем...";

    try {
      await request("/api/team/settings/", {
        method: "POST",
        body: JSON.stringify({
          captain_telegram_id: Number(currentTelegramId),
          team_id: teamId,
          name: nameInput.value.trim(),
          description: descriptionInput.value.trim(),
          tech_stack: techStackInput.value.trim(),
          vacancies: vacanciesInput.value.trim(),
          is_open: toggle.checked,
          max_members: Number(maxInput.value),
        }),
      });

      setCaptainMessage("Настройки команды сохранены");
      await loadProfile();
    } catch (error) {
      setCaptainMessage(error.message, true);
    } finally {
      saveBtn.disabled = false;
      saveBtn.textContent = "Сохранить настройки";
    }
  });
}

async function buildCaptainPanel(user, membershipData) {
  try {
    const memberships = Array.isArray(membershipData) ? membershipData : [];
    const captainTeamMembership = memberships.find((item) => {
      return (
        String(item.user?.telegram_id || "") === String(user.telegram_id) &&
        String(item.team?.captain?.telegram_id || "") === String(user.telegram_id) &&
        item.status === "accepted"
      );
    });

    const captainTeam = captainTeamMembership?.team;
    if (!captainTeam) {
      return "";
    }

    const acceptedMembers = memberships.filter((item) => {
      return Number(item.team?.id) === Number(captainTeam.id) && item.status === "accepted";
    });

    let requests = [];
    try {
      const requestsData = await request(`/api/team/requests/${user.telegram_id}/`);
      requests = requestsData.requests || [];
    } catch (error) {
      requests = [];
    }

        return `
      <section class="captain-panel" data-team-id="${captainTeam.id}">
        <div class="captain-panel-header">
          <h3>Панель капитана</h3>
        </div>
    
        <div id="captain-message" class="message hidden"></div>
    
        <div class="captain-panel-grid">
          <div class="profile-row">
            <span class="profile-label">Команда</span>
            <strong>${escapeHtml(captainTeam.name)}</strong>
          </div>
    
          <div class="profile-row">
            <span class="profile-label">Участники</span>
            <strong>${acceptedMembers.length} / ${captainTeam.max_members || 5}</strong>
          </div>
    
          <div class="profile-row">
            <span class="profile-label">Набор</span>
            <strong>${captainTeam.is_open ? "Открыт" : "Закрыт"}</strong>
          </div>
        </div>
    
        <div class="captain-settings">
          <label class="field">
            <span class="profile-label">Название команды</span>
            <input id="team-name" class="input" type="text" value="${escapeHtml(captainTeam.name)}">
          </label>
    
          <label class="field">
            <span class="profile-label">Описание</span>
            <textarea id="team-description" class="input textarea" rows="3">${escapeHtml(captainTeam.description || "")}</textarea>
          </label>
    
          <label class="field">
            <span class="profile-label">Технологический стек</span>
            <textarea id="team-tech-stack" class="input textarea" rows="2">${escapeHtml(captainTeam.tech_stack || "")}</textarea>
          </label>
    
          <label class="field">
            <span class="profile-label">Вакансии</span>
            <textarea id="team-vacancies" class="input textarea" rows="2">${escapeHtml(captainTeam.vacancies || "")}</textarea>
          </label>
    
          <label class="field">
            <span class="profile-label">Открыт набор</span>
            <input id="team-open-toggle" type="checkbox" ${captainTeam.is_open ? "checked" : ""}>
          </label>
    
          <label class="field">
            <span class="profile-label">Лимит участников</span>
            <input id="team-max-members" class="input" type="number" min="1" value="${captainTeam.max_members || 5}">
          </label>
    
          <button id="team-settings-save" class="button primary" type="button">
            Сохранить настройки
          </button>
        </div>
    
        <div class="captain-requests">
          <span class="profile-label">Входящие заявки</span>
          ${renderCaptainRequests(requests)}
        </div>
      </section>
    `;
  } catch (error) {
    return `
      <section class="captain-panel">
        <div class="captain-panel-header">
          <h3>Панель капитана</h3>
        </div>
        <div class="muted">Не удалось загрузить данные капитана.</div>
      </section>
    `;
  }
}

function buildCreateTeamBlock() {
  return `
    <section class="create-team-panel">
      <div class="create-team-header">
        <h3>Создать команду</h3>
        <button id="create-team-toggle" class="button secondary" type="button">
          Открыть форму
        </button>
      </div>

      <div id="create-team-message" class="message hidden"></div>

      <form id="create-team-form" class="create-team-form hidden">
        <label class="field">
          <span class="profile-label">Название команды</span>
          <input class="input" name="name" type="text" placeholder="Backend Builders" required />
        </label>

        <label class="field">
          <span class="profile-label">Описание</span>
          <textarea class="input textarea" name="description" rows="3" placeholder="Коротко опишите идею" required></textarea>
        </label>

        <label class="field">
          <span class="profile-label">Технологический стек</span>
          <input class="input" name="tech_stack" type="text" placeholder="Python, Django, PostgreSQL" required />
        </label>

        <label class="field">
          <span class="profile-label">Вакансии</span>
          <input class="input" name="vacancies" type="text" placeholder="Frontend, Designer" required />
        </label>

        <button class="button primary" type="submit">Создать команду</button>
      </form>
    </section>
  `;
}

function renderCaptainRequests(requests) {
  if (!requests.length) {
    return '<div class="muted">Новых заявок пока нет.</div>';
  }

  return `
    <div class="request-list">
      ${requests.map((item) => `
        <div class="request-item">
          <strong>${escapeHtml(item.user?.full_name || "Без имени")}</strong>
          <div class="muted">${escapeHtml(item.user?.email || "Email не указан")}</div>
          <div class="muted">${escapeHtml(item.user?.skills || "Навыки не указаны")}</div>
          <div class="muted">Статус: ${escapeHtml(item.status || "unknown")}</div>
          <div class="muted">Команда: ${escapeHtml(item.team?.name || "Без названия")}</div>
          <div class="request-actions">
            <button
              class="button primary request-action"
              type="button"
              data-decision="accept"
              data-user-telegram-id="${item.user?.telegram_id || ""}"
              data-team-id="${item.team?.id || ""}"
            >
              Принять
            </button>
            <button
              class="button secondary request-action"
              type="button"
              data-decision="reject"
              data-user-telegram-id="${item.user?.telegram_id || ""}"
              data-team-id="${item.team?.id || ""}"
            >
              Отклонить
            </button>
          </div>
        </div>
      `).join("")}
    </div>
  `;
}

function bindCaptainRequestActions() {
  document.querySelectorAll(".request-action").forEach((button) => {
    button.addEventListener("click", () => handleCaptainDecision(button));
  });

  if (profileFlashMessage) {
    setCaptainMessage(profileFlashMessage.text, profileFlashMessage.isError);
    profileFlashMessage = null;
  }
}

function setCaptainMessage(text, isError = false) {
  const captainMessage = document.getElementById("captain-message");
  if (!captainMessage) {
    return;
  }

  captainMessage.textContent = text;
  captainMessage.classList.toggle("error", isError);
  captainMessage.classList.remove("hidden");
}

async function handleCaptainDecision(button) {
  const userTelegramId = Number(button.dataset.userTelegramId);
  const teamId = Number(button.dataset.teamId);
  const decision = button.dataset.decision;

  document.querySelectorAll(".request-action").forEach((item) => {
    item.disabled = true;
  });
  button.textContent = decision === "accept" ? "Принимаем..." : "Отклоняем...";

  try {
    await request("/api/team/decision/", {
      method: "POST",
      body: JSON.stringify({
        captain_telegram_id: Number(currentTelegramId),
        user_telegram_id: userTelegramId,
        team_id: teamId,
        decision: decision,
      }),
    });

    profileFlashMessage = {
      text: decision === "accept" ? "Заявка принята" : "Заявка отклонена",
      isError: false,
    };
    await loadProfile();
  } catch (error) {
    document.querySelectorAll(".request-action").forEach((item) => {
      item.disabled = false;
    });
    button.textContent = decision === "accept" ? "Принять" : "Отклонить";
    setCaptainMessage(error.message, true);
  }
}

async function loadTeams() {
  showScreen("teams-screen");
  teamsList.innerHTML = '<div class="panel muted">Загрузка команд...</div>';

  try {
    const data = await request("/api/team/list/");
    allTeams = data.teams || [];
    renderTechStackOptions(allTeams);
    applyFilters();
  } catch (error) {
    teamsList.innerHTML = "";
    showMessage(error.message, true);
  }
}

function renderTechStackOptions(teams) {
  const values = new Set();

  teams.forEach((team) => {
    String(team.tech_stack || "")
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean)
      .forEach((item) => values.add(item));
  });

  const currentValue = techStackFilter.value;
  techStackFilter.innerHTML = '<option value="">Все технологии</option>';

  [...values].sort((a, b) => a.localeCompare(b, "ru")).forEach((value) => {
    techStackFilter.insertAdjacentHTML(
      "beforeend",
      `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`
    );
  });

  techStackFilter.value = currentValue;
}

function applyFilters() {
  const searchText = teamSearchInput.value.trim().toLowerCase();
  const techStackValue = techStackFilter.value.trim().toLowerCase();

  const filteredTeams = allTeams.filter((team) => {
    const haystack = [
      team.name,
      team.description,
      team.tech_stack,
      team.vacancies,
    ]
      .join(" ")
      .toLowerCase();

    const matchesText = !searchText || haystack.includes(searchText);
    const matchesTechStack =
      !techStackValue || String(team.tech_stack || "").toLowerCase().includes(techStackValue);

    return matchesText && matchesTechStack;
  });

  renderTeams(filteredTeams);
}

function renderTeams(teams) {
  if (!teams.length) {
    teamsList.innerHTML = '<div class="panel muted">Команды по текущему фильтру не найдены.</div>';
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
    showMessage("Заявка отправлена");
  } catch (error) {
    button.disabled = false;
    button.textContent = "Откликнуться";
    showMessage(error.message, true);
  }
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
teamSearchInput.addEventListener("input", applyFilters);
techStackFilter.addEventListener("change", applyFilters);

document.querySelectorAll("[data-screen]").forEach((button) => {
  button.addEventListener("click", () => showScreen(button.dataset.screen));
});

if (tg) {
  tg.ready();
  tg.expand();
} else {
  devHint.classList.remove("hidden");
}

currentTelegramId = getTelegramId();
