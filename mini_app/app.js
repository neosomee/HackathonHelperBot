/**
 * HackathonHelper Telegram Mini App
 * API: same origin as the Mini App (Django), пути /api/...
 */
const tg = window.Telegram?.WebApp;

const apiBaseUrl = window.location.origin;

const state = {
  telegramId: null,
  user: null,
  memberships: [],
  teams: [],
  teamsLoaded: false,
  editing: false,
};

const els = {
  toast: document.getElementById("toast"),
  profileHint: document.getElementById("profile-hint"),
  notRegistered: document.getElementById("profile-not-registered"),
  profileContent: document.getElementById("profile-content"),
  profileForm: document.getElementById("profile-form"),
  profileFormSave: document.getElementById("profile-form-save"),
  profileFormCancel: document.getElementById("profile-form-cancel"),
  screenProfile: document.getElementById("screen-profile"),
  screenSearch: document.getElementById("screen-search"),
  tabProfile: document.getElementById("tab-profile"),
  tabSearch: document.getElementById("tab-search"),
  teamsList: document.getElementById("teams-list"),
  searchMessage: document.getElementById("search-message"),
  filterStack: document.getElementById("filter-stack"),
  filterVacancy: document.getElementById("filter-vacancy"),
  teamsFilterMeta: document.getElementById("teams-filter-meta"),
  btnRefreshTeams: document.getElementById("btn-refresh-teams"),
};

function getTelegramId() {
  const fromTg = tg?.initDataUnsafe?.user?.id;
  if (fromTg) {
    return Number(fromTg);
  }
  const q = new URLSearchParams(window.location.search).get("telegram_id");
  return q ? Number(q) : null;
}

function getCsrfToken() {
  const m = document.cookie.match(/csrftoken=([^;]+)/);
  return m ? decodeURIComponent(m[1]) : "";
}

function applyTelegramTheme() {
  if (!tg?.themeParams) {
    return;
  }
  const t = tg.themeParams;
  const root = document.documentElement;
  if (t.bg_color) {
    root.style.setProperty("--bg", t.bg_color);
  }
  if (t.text_color) {
    root.style.setProperty("--text", t.text_color);
  }
  if (t.hint_color) {
    root.style.setProperty("--muted", t.hint_color);
  }
  if (t.button_color) {
    root.style.setProperty("--primary", t.button_color);
  }
  if (t.button_text_color) {
    root.style.setProperty("--on-primary", t.button_text_color);
  }
  if (t.secondary_bg_color) {
    root.style.setProperty("--surface", t.secondary_bg_color);
  }
  const scheme = t.bg_color
    ? /fff|f6f6|ebed/i.test(t.bg_color) ? "light" : "dark"
    : (tg.colorScheme || "light");
  root.style.colorScheme = scheme;
}

async function request(path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };
  const csrf = getCsrfToken();
  if (csrf && (options.method === "POST" || options.method === "PUT" || options.method === "DELETE")) {
    headers["X-CSRFToken"] = csrf;
  }

  const response = await fetch(`${apiBaseUrl}${path}`, {
    credentials: "same-origin",
    ...options,
    headers,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const err = new Error(getErrorMessage(data));
    err.status = response.status;
    err.body = data;
    throw err;
  }
  return data;
}

function getErrorMessage(data) {
  if (data?.error) {
    return data.error;
  }
  if (data?.errors) {
    return "Проверьте данные и попробуйте снова.";
  }
  return "Не удалось выполнить запрос.";
}

function showToast(text, isError = false) {
  els.toast.textContent = text;
  els.toast.classList.toggle("error", isError);
  els.toast.classList.remove("hidden");
  clearTimeout(showToast._t);
  showToast._t = setTimeout(() => els.toast.classList.add("hidden"), 4500);
}

function hideSearchMessage() {
  els.searchMessage.textContent = "";
  els.searchMessage.classList.add("hidden");
  els.searchMessage.classList.remove("error");
}

function showSearchMessage(text, isError = false) {
  els.searchMessage.textContent = text;
  els.searchMessage.classList.toggle("error", isError);
  els.searchMessage.classList.remove("hidden");
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

/**
 * DRF: без пагинации — массив; с пагинацией — { results: [...] }.
 */
function normalizeList(data) {
  if (Array.isArray(data)) {
    return data;
  }
  if (data && Array.isArray(data.results)) {
    return data.results;
  }
  return [];
}

function getMembershipsForUser(memberships, user) {
  if (!user) {
    return [];
  }
  return memberships.filter((m) => m.user && m.user.id === user.id);
}

function getParticipationInfo(user, mine) {
  const accepted = mine.find((m) => m.status === "accepted");
  const pending = mine.filter((m) => m.status === "pending");
  if (accepted && accepted.team) {
    const isCaptain = accepted.team.captain && user.id === accepted.team.captain.id;
    return {
      line: isCaptain
        ? `Статус: <strong>капитан</strong> команды «${escapeHtml(accepted.team.name)}»`
        : `Статус: <strong>участник</strong> команды «${escapeHtml(accepted.team.name)}»`,
    };
  }
  if (pending.length) {
    const names = pending.map((m) => (m.team ? m.team.name : "—")).filter(Boolean);
    return {
      line: `Статус: <strong>не в команде</strong>. Ожидают рассмотрения: ${escapeHtml(names.join(", "))}`,
    };
  }
  return { line: "Статус: <strong>не в команде</strong>." };
}

function userInTeam(mine) {
  return mine.some((m) => m.status === "accepted");
}

function findMembershipForTeam(mine, teamId) {
  return mine.find((m) => m.team && m.team.id === teamId);
}

function renderProfileRead() {
  const { user, memberships } = state;
  if (!user) {
    return;
  }
  const mine = getMembershipsForUser(memberships, user);
  const part = getParticipationInfo(user, mine);

  els.profileContent.innerHTML = `
    <div class="card">
      <div class="profile-row">
        <span class="label">ФИО</span>
        <div class="value">${escapeHtml(user.full_name)}</div>
      </div>
      <div class="profile-row">
        <span class="label">Почта</span>
        <div class="value">${escapeHtml(user.email)}</div>
      </div>
      <div class="profile-row">
        <span class="label">Технологический стек</span>
        <div class="value pre">${escapeHtml(user.skills)}</div>
      </div>
      <div class="profile-row participation" role="status">
        <span class="label">Участие</span>
        <div class="value">${part.line}</div>
      </div>
      <p class="tip muted">Создание команды — в боте. Здесь можно обновить профиль и откликнуться на вакансии.</p>
      <div class="profile-actions">
        <button type="button" class="button primary" id="btn-edit-profile">Редактировать</button>
        <button type="button" class="link-like" id="btn-reload-profile" title="Повторить запрос">Обновить</button>
      </div>
    </div>
  `;
  document.getElementById("btn-edit-profile").addEventListener("click", startEditProfile);
  document.getElementById("btn-reload-profile").addEventListener("click", () => {
    loadProfileData(true);
  });
}

function startEditProfile() {
  if (!state.user) {
    return;
  }
  state.editing = true;
  const f = els.profileForm;
  f.full_name.value = state.user.full_name || "";
  f.email.value = state.user.email || "";
  f.skills.value = state.user.skills || "";
  f.classList.remove("hidden");
  els.profileContent.classList.add("hidden");
  els.profileHint.textContent = "Измените поля и нажмите «Сохранить».";
}

function cancelEditProfile() {
  state.editing = false;
  els.profileForm.classList.add("hidden");
  els.profileContent.classList.remove("hidden");
  els.profileHint.textContent = "Данные из базы, общие с ботом.";
}

async function loadProfileData(showFeedback = false) {
  if (!state.telegramId) {
    els.profileHint.textContent = "Откройте Mini App из Telegram (или добавьте ?telegram_id= для отладки).";
    els.notRegistered.classList.add("hidden");
    els.profileContent.classList.add("hidden");
    return;
  }

  els.notRegistered.classList.add("hidden");
  els.profileContent.classList.add("hidden");
  els.profileForm.classList.add("hidden");
  els.profileHint.textContent = "Загрузка профиля…";

  try {
    const [profileRes, membersRes] = await Promise.all([
      request(`/api/profile/${state.telegramId}/`),
      request("/api/team-members/").catch(() => []),
    ]);
    state.user = profileRes.user;
    state.memberships = normalizeList(membersRes);
    if (state.editing) {
      state.editing = false;
    }
    els.profileHint.textContent = "Данные из базы, общие с ботом.";
    els.profileContent.classList.remove("hidden");
    renderProfileRead();
    if (showFeedback) {
      showToast("Профиль обновлён");
    }
  } catch (e) {
    if (e.status === 404) {
      state.user = null;
      state.memberships = [];
      els.profileHint.textContent = "";
      els.notRegistered.classList.remove("hidden");
    } else {
      els.profileHint.textContent = "Не удалось загрузить профиль.";
      els.profileContent.innerHTML = `<div class="card error-block"><p>${escapeHtml(e.message)}</p>
        <button type="button" class="button secondary" id="btn-retry-profile">Повторить</button></div>`;
      els.profileContent.classList.remove("hidden");
      document.getElementById("btn-retry-profile")?.addEventListener("click", () => loadProfileData());
    }
  }
}

async function saveProfile(event) {
  event.preventDefault();
  const f = els.profileForm;
  if (!state.telegramId || !state.user) {
    return;
  }
  const payload = {
    telegram_id: state.telegramId,
    full_name: f.full_name.value.trim(),
    email: f.email.value.trim(),
    skills: f.skills.value.trim(),
  };
  if (!payload.full_name || !payload.email || !payload.skills) {
    showToast("Заполните ФИО, email и стек.", true);
    return;
  }

  els.profileFormSave.disabled = true;
  try {
    const data = await request("/api/profile/update/", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    state.user = data.user;
    cancelEditProfile();
    renderProfileRead();
    els.profileContent.classList.remove("hidden");
    showToast("Сохранено");
  } catch (e) {
    showToast(e.message, true);
  } finally {
    els.profileFormSave.disabled = false;
  }
}

function getFilteredTeams() {
  const stackQ = (els.filterStack.value || "").trim().toLowerCase();
  const vacQ = (els.filterVacancy.value || "").trim().toLowerCase();
  return state.teams.filter((team) => {
    if (stackQ && !String(team.tech_stack || "").toLowerCase().includes(stackQ)) {
      return false;
    }
    if (vacQ && !String(team.vacancies || "").toLowerCase().includes(vacQ)) {
      return false;
    }
    return true;
  });
}

function updateFilterMeta() {
  const total = state.teams.length;
  const n = getFilteredTeams().length;
  els.teamsFilterMeta.textContent =
    total === 0
      ? "Список команд пуст"
      : `Показано: ${n} из ${total} (фильтрация в приложении)`;
}

function renderTeams() {
  const mine = getMembershipsForUser(state.memberships, state.user);
  const inTeam = userInTeam(mine);
  const filtered = getFilteredTeams();
  if (!state.teams.length) {
    els.teamsList.innerHTML = '<div class="card muted">Пока нет открытых команд.</div>';
    updateFilterMeta();
    return;
  }
  if (!filtered.length) {
    els.teamsList.innerHTML = '<div class="card muted">Нет совпадений. Измените фильтры.</div>';
    updateFilterMeta();
    return;
  }
  const html = filtered
    .map((team) => {
      const m = findMembershipForTeam(mine, team.id);
      const pendingHere = m && m.status === "pending";
      const acceptedHere = m && m.status === "accepted";
      const canClick =
        Boolean(team.is_open) &&
        !inTeam &&
        !pendingHere &&
        !acceptedHere;
      const btnText = acceptedHere
        ? "Вы в этой команде"
        : pendingHere
        ? "Заявка отправлена"
        : inTeam
        ? "Уже в команде"
        : !team.is_open
        ? "Набор закрыт"
        : "Откликнуться";
      const btnClass =
        canClick && team.is_open ? "button primary" : "button secondary";

      return `
    <article class="team-card card" data-team-id="${team.id}">
      <div class="team-card-head" role="button" tabindex="0" aria-expanded="false">
        <h2 class="team-title">${escapeHtml(team.name)}</h2>
        <span class="status-pill">${team.is_open ? "Набор открыт" : "Набор закрыт"}</span>
      </div>
      <p class="muted team-excerpt">${escapeHtml((team.description || "").slice(0, 200))}${
    (team.description || "").length > 200 ? "…" : ""
  }</p>
      <div class="team-details hidden">
        <p class="pre">${escapeHtml(team.description || "")}</p>
        <div class="meta-grid">
          <div><span class="label">Стек</span><div class="pre">${escapeHtml(team.tech_stack || "—")}</div></div>
          <div><span class="label">Вакансии</span><div class="pre">${escapeHtml(team.vacancies || "—")}</div></div>
        </div>
      </div>
      <div class="team-actions">
        <button type="button" class="${btnClass} apply-btn" data-team-id="${team.id}" ${
    canClick ? "" : "disabled"
  }>
          ${btnText}
        </button>
      </div>
    </article>`;
    })
    .join("");

  els.teamsList.innerHTML = html;
  els.teamsList.querySelectorAll(".team-card-head").forEach((head) => {
    head.addEventListener("click", () => toggleCard(head));
    head.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter" || ev.key === " ") {
        ev.preventDefault();
        toggleCard(head);
      }
    });
  });
  els.teamsList.querySelectorAll(".apply-btn").forEach((btn) => {
    btn.addEventListener("click", () => applyToTeam(btn));
  });
  updateFilterMeta();
}

function toggleCard(head) {
  const card = head.closest(".team-card");
  const det = card.querySelector(".team-details");
  const ex = card.querySelector(".team-excerpt");
  const isOpen = !det.classList.contains("hidden");
  if (isOpen) {
    det.classList.add("hidden");
    ex.classList.remove("hidden");
    head.setAttribute("aria-expanded", "false");
  } else {
    det.classList.remove("hidden");
    ex.classList.add("hidden");
    head.setAttribute("aria-expanded", "true");
  }
}

async function loadTeamsData() {
  hideSearchMessage();
  els.teamsList.innerHTML = '<div class="card muted">Загрузка команд…</div>';
  try {
    const data = await request("/api/team/list/");
    state.teams = data.teams || [];
    state.teamsLoaded = true;
    if (state.user) {
      const membersRes = await request("/api/team-members/").catch(() => []);
      state.memberships = normalizeList(membersRes);
    }
    renderTeams();
  } catch (e) {
    els.teamsList.innerHTML = "";
    showSearchMessage(e.message, true);
  }
}

function mapApplicationError(err) {
  const msg = err.message || "";
  if (msg.includes("already in a team") || err.status === 409) {
    if (msg.includes("User is already in a team")) {
      return "Вы уже состоите в команде.";
    }
  }
  if (msg.includes("Application already exists")) {
    return "Вы уже отправили заявку в эту команду.";
  }
  if (msg.includes("Team is closed")) {
    return "Команда уже закрыла набор.";
  }
  return msg || "Ошибка заявки";
}

async function applyToTeam(button) {
  if (!state.telegramId) {
    showSearchMessage("Откройте Mini App из Telegram, чтобы отправить заявку.", true);
    return;
  }
  if (!state.user) {
    showSearchMessage("Сначала зарегистрируйтесь в боте.", true);
    return;
  }
  const teamId = Number(button.dataset.teamId);
  button.disabled = true;
  const prev = button.textContent;
  button.textContent = "Отправка…";
  try {
    await request("/api/team/apply/", {
      method: "POST",
      body: JSON.stringify({
        user_telegram_id: state.telegramId,
        team_id: teamId,
      }),
    });
    showSearchMessage("Заявка отправлена. Капитан получит уведомление в боте.");
    await loadContextAfterApply();
  } catch (e) {
    button.disabled = false;
    button.textContent = prev;
    showSearchMessage(mapApplicationError(e), true);
  }
}

async function loadContextAfterApply() {
  if (!state.telegramId) {
    return;
  }
  const membersRes = await request("/api/team-members/").catch(() => []);
  state.memberships = normalizeList(membersRes);
  renderTeams();
  if (els.screenSearch.classList.contains("active") === false) {
    return;
  }
}

function showScreen(screenId) {
  const isProfile = screenId === "screen-profile";
  els.screenProfile.classList.toggle("active", isProfile);
  els.screenSearch.classList.toggle("active", !isProfile);
  els.tabProfile.classList.toggle("active", isProfile);
  els.tabSearch.classList.toggle("active", !isProfile);
  els.tabProfile.setAttribute("aria-selected", String(isProfile));
  els.tabSearch.setAttribute("aria-selected", String(!isProfile));
  if (screenId === "screen-search" && !state.teamsLoaded) {
    loadTeamsData();
  }
  hideSearchMessage();
}

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    const id = tab.getAttribute("data-screen");
    if (id) {
      showScreen(id);
    }
  });
});

els.profileForm.addEventListener("submit", saveProfile);
els.profileFormCancel.addEventListener("click", () => {
  cancelEditProfile();
  renderProfileRead();
  els.profileContent.classList.remove("hidden");
  els.profileHint.textContent = "Данные из базы, общие с ботом.";
});

let filterDebounce;
["input", "change"].forEach((ev) => {
  els.filterStack.addEventListener(ev, () => {
    clearTimeout(filterDebounce);
    filterDebounce = setTimeout(() => {
      if (state.teamsLoaded) {
        renderTeams();
      }
    }, 200);
  });
  els.filterVacancy.addEventListener(ev, () => {
    clearTimeout(filterDebounce);
    filterDebounce = setTimeout(() => {
      if (state.teamsLoaded) {
        renderTeams();
      }
    }, 200);
  });
});

if (tg) {
  tg.ready();
  tg.expand();
}
applyTelegramTheme();

state.telegramId = getTelegramId();
loadProfileData();
showScreen("screen-profile");

els.btnRefreshTeams.addEventListener("click", () => {
  state.teamsLoaded = false;
  state.teams = [];
  loadTeamsData();
});
