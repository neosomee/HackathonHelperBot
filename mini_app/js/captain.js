import { request } from "./api.js";
import { escapeHtml } from "./utils.js";

export async function syncCaptainButtonVisibility({ state, els }) {
  const captainButton = document.getElementById("captain-button");
  if (!captainButton || !state.currentTelegramId) return;

  try {
    const profileData = await request(`/api/profile/${state.currentTelegramId}/`);
    const user = profileData.user;
    const isCaptain = Boolean(user.is_kaptain || user.role === "CAPTAIN");

    captainButton.classList.toggle("hidden", !isCaptain);

    if (!isCaptain && els.captainDashboard) {
      els.captainDashboard.classList.add("hidden");
      els.captainDashboard.innerHTML = "";
    }
  } catch {
    captainButton.classList.add("hidden");
  }
}

export async function loadCaptainDashboard({ state, els }) {
  const { captainDashboard } = els;
  if (!captainDashboard || !state.currentTelegramId) return;

  try {
    const profileData = await request(`/api/profile/${state.currentTelegramId}/`);
    const user = profileData.user;

    if (!(user.is_kaptain || user.role === "CAPTAIN")) {
      captainDashboard.innerHTML = `
        <section class="captain-panel">
          <div class="captain-panel-header">
            <h3>Панель капитана</h3>
          </div>
          <div class="muted">У вас нет доступа к панели капитана.</div>
        </section>
      `;
      return;
    }

    const membershipData = await request("/api/team-members/");
    const captainTeamMembership = membershipData.find((item) => {
      return (
        String(item.user?.telegram_id || "") === String(user.telegram_id) &&
        String(item.team?.captain?.telegram_id || "") === String(user.telegram_id) &&
        item.status === "accepted"
      );
    });

    const captainTeam = captainTeamMembership?.team;
    if (!captainTeam) {
      captainDashboard.innerHTML = `
        <section class="captain-panel">
          <div class="captain-panel-header">
            <h3>Панель капитана</h3>
          </div>
          <div class="muted">У вас пока нет команды. Создайте её в профиле.</div>
        </section>
      `;
      return;
    }

    const acceptedMembers = membershipData.filter((item) => {
      return Number(item.team?.id) === Number(captainTeam.id) && item.status === "accepted";
    });

    let requests = [];
    try {
      const requestsData = await request(`/api/team/requests/${user.telegram_id}/`);
      requests = requestsData.requests || [];
    } catch {
      requests = [];
    }

    let hackathons = [];
    try {
      const qs = new URLSearchParams({
        captain_telegram_id: String(user.telegram_id),
        user_telegram_id: String(user.telegram_id),
      });
      const hackathonsRes = await request(`/api/hackathons/?${qs.toString()}`);
      hackathons = hackathonsRes.hackathons || [];
    } catch {
      hackathons = [];
    }

    captainDashboard.innerHTML = `
      <section class="captain-panel" data-team-id="${captainTeam.id}">
        <div class="captain-panel-header">
          <h3>Панель капитана</h3>
          <p class="muted">Настройки команды, состав и заявки.</p>
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

        <div class="captain-hackathons">
          <span class="profile-label">Хакатоны</span>
          <p class="muted">Подключение команды к событию (только капитан).</p>
          ${renderHackathonRows(hackathons)}
        </div>

        <div class="captain-members">
          <span class="profile-label">Участники команды</span>
          ${renderCaptainMembers(acceptedMembers)}
        </div>

        <div class="captain-requests">
          <span class="profile-label">Входящие заявки</span>
          ${renderCaptainRequests(requests)}
        </div>
      </section>
    `;

    bindCaptainRequestActions(state, els);
    bindCaptainSettingsActions(state, els);
    bindHackathonJoinActions(state, els);
    bindScheduleSubscriptionActions(state, els);
  } catch (error) {
    captainDashboard.innerHTML = `
      <section class="captain-panel">
        <div class="captain-panel-header">
          <h3>Панель капитана</h3>
        </div>
        <div class="muted">Не удалось загрузить данные капитана.</div>
      </section>
    `;
  }
}

function renderHackathonRows(items) {
  if (!items.length) {
    return '<div class="muted-box">Нет хакатонов с открытым подключением команд.</div>';
  }

  return `
    <div class="hackathon-list">
      ${items
        .map(
          (h) => `
        <div class="hackathon-card muted-box">
          <strong>${escapeHtml(h.name)}</strong>
          ${
            h.schedule_sheet_url
              ? `<div><a class="link-like" href="${escapeHtml(h.schedule_sheet_url)}" target="_blank" rel="noopener noreferrer">Расписание (Google Таблица)</a></div>`
              : ""
          }
          ${
            h.my_team_enrolled
              ? '<p class="muted">Команда уже подключена к этому хакатону.</p>'
              : `<button type="button" class="button primary hackathon-join-btn" data-hackathon-id="${h.id}">Подключить команду</button>`
          }
          ${
            h.my_team_enrolled && h.schedule_sheet_url
              ? `<div class="schedule-subscribe-wrap">
                <button type="button" class="button secondary schedule-subscribe-btn"
                  data-hackathon-id="${h.id}"
                  data-subscribed="${h.schedule_subscribed ? "1" : "0"}">
                  ${
                    h.schedule_subscribed
                      ? "Отписаться от напоминаний"
                      : "Включить напоминания по расписанию"
                  }
                </button>
                <p class="muted tip">Таблица должна быть по формату в docs/SCHEDULE_CSV_FORMAT.md; на сервере — Redis + Celery worker/beat.</p>
              </div>`
              : ""
          }
        </div>
      `
        )
        .join("")}
    </div>
  `;
}

function bindHackathonJoinActions(state, els) {
  const buttons = els.captainDashboard?.querySelectorAll(".hackathon-join-btn") || [];
  buttons.forEach((btn) => {
    btn.addEventListener("click", async () => {
      const hackathonId = Number(btn.dataset.hackathonId);
      btn.disabled = true;
      try {
        await request(`/api/hackathons/${hackathonId}/join-team/`, {
          method: "POST",
          body: JSON.stringify({
            captain_telegram_id: Number(state.currentTelegramId),
          }),
        });
        setCaptainMessage(els, "Команда подключена к хакатону.");
        await loadCaptainDashboard({ state, els });
      } catch (error) {
        setCaptainMessage(els, error.message, true);
        btn.disabled = false;
      }
    });
  });
}

function bindScheduleSubscriptionActions(state, els) {
  const buttons = els.captainDashboard?.querySelectorAll(".schedule-subscribe-btn") || [];
  buttons.forEach((btn) => {
    btn.addEventListener("click", async () => {
      const hackathonId = Number(btn.dataset.hackathonId);
      const subscribed = btn.dataset.subscribed === "1";
      const path = subscribed
        ? `/api/hackathons/${hackathonId}/schedule/unsubscribe/`
        : `/api/hackathons/${hackathonId}/schedule/subscribe/`;
      btn.disabled = true;
      try {
        await request(path, {
          method: "POST",
          body: JSON.stringify({
            telegram_id: Number(state.currentTelegramId),
          }),
        });
        setCaptainMessage(
          els,
          subscribed ? "Напоминания по расписанию отключены." : "Напоминания включены."
        );
        await loadCaptainDashboard({ state, els });
      } catch (error) {
        setCaptainMessage(els, error.message, true);
        btn.disabled = false;
      }
    });
  });
}

function renderCaptainMembers(members) {
  if (!members.length) {
    return '<div class="muted-box">В команде пока нет участников.</div>';
  }

  return `
    <div class="member-list">
      ${members
        .map(
          (item) => `
        <article class="member-card">
          <strong>${escapeHtml(item.user?.full_name || "Без имени")}</strong>
          <div class="muted">${escapeHtml(item.user?.email || "Email не указан")}</div>
          <div class="muted">Навыки: ${escapeHtml(item.user?.skills || "не указаны")}</div>
          <div class="muted">Статус: ${escapeHtml(item.status || "unknown")}</div>
        </article>
      `
        )
        .join("")}
    </div>
  `;
}

function renderCaptainRequests(requests) {
  if (!requests.length) {
    return '<div class="muted">Новых заявок пока нет.</div>';
  }

  return `
    <div class="request-list">
      ${requests
        .map(
          (item) => `
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
      `
        )
        .join("")}
    </div>
  `;
}

function setCaptainMessage(els, text, isError = false) {
  const captainMessage = els.captainDashboard?.querySelector("#captain-message");
  if (!captainMessage) return;

  captainMessage.textContent = text;
  captainMessage.classList.toggle("error", isError);
  captainMessage.classList.remove("hidden");
}

function bindCaptainRequestActions(state, els) {
  const buttons = els.captainDashboard?.querySelectorAll(".request-action") || [];
  buttons.forEach((button) => {
    button.addEventListener("click", () => handleCaptainDecision(state, els, button));
  });
}

function bindCaptainSettingsActions(state, els) {
  const saveBtn = els.captainDashboard?.querySelector("#team-settings-save");
  const panel = els.captainDashboard?.querySelector(".captain-panel");
  const toggle = els.captainDashboard?.querySelector("#team-open-toggle");
  const maxInput = els.captainDashboard?.querySelector("#team-max-members");
  const nameInput = els.captainDashboard?.querySelector("#team-name");
  const descriptionInput = els.captainDashboard?.querySelector("#team-description");
  const techStackInput = els.captainDashboard?.querySelector("#team-tech-stack");
  const vacanciesInput = els.captainDashboard?.querySelector("#team-vacancies");

  const teamId = Number(panel?.dataset.teamId);
  if (
    !saveBtn ||
    !panel ||
    !toggle ||
    !maxInput ||
    !nameInput ||
    !descriptionInput ||
    !techStackInput ||
    !vacanciesInput ||
    !teamId
  ) {
    return;
  }

  saveBtn.addEventListener("click", async () => {
    saveBtn.disabled = true;
    saveBtn.textContent = "Сохраняем...";

    try {
      await request("/api/team/settings/", {
        method: "POST",
        body: JSON.stringify({
          captain_telegram_id: Number(state.currentTelegramId),
          team_id: teamId,
          name: nameInput.value.trim(),
          description: descriptionInput.value.trim(),
          tech_stack: techStackInput.value.trim(),
          vacancies: vacanciesInput.value.trim(),
          is_open: toggle.checked,
          max_members: Number(maxInput.value),
        }),
      });

      setCaptainMessage(els, "Настройки команды сохранены");
      await loadCaptainDashboard({ state, els });
    } catch (error) {
      setCaptainMessage(els, error.message, true);
    } finally {
      saveBtn.disabled = false;
      saveBtn.textContent = "Сохранить настройки";
    }
  });
}

async function handleCaptainDecision(state, els, button) {
  const userTelegramId = Number(button.dataset.userTelegramId);
  const teamId = Number(button.dataset.teamId);
  const decision = button.dataset.decision;

  (els.captainDashboard?.querySelectorAll(".request-action") || []).forEach((item) => {
    item.disabled = true;
  });

  button.textContent = decision === "accept" ? "Принимаем..." : "Отклоняем...";

  try {
    await request("/api/team/decision/", {
      method: "POST",
      body: JSON.stringify({
        captain_telegram_id: Number(state.currentTelegramId),
        user_telegram_id: userTelegramId,
        team_id: teamId,
        decision,
      }),
    });

    setCaptainMessage(
      els,
      decision === "accept" ? "Заявка принята" : "Заявка отклонена"
    );
    await loadCaptainDashboard({ state, els });
  } catch (error) {
    (els.captainDashboard?.querySelectorAll(".request-action") || []).forEach((item) => {
      item.disabled = false;
    });
    button.textContent = decision === "accept" ? "Принять" : "Отклонить";
    setCaptainMessage(els, error.message, true);
  }
}