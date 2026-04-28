import { request } from "./api.js";
import {
  clearMessage,
  escapeHtml,
  getMembershipInfo,
  showScreen,
} from "./utils.js";

function getCaptainContext(membershipData, currentTelegramId) {
  const memberships = Array.isArray(membershipData) ? membershipData : [];

  const captainMembership = memberships.find((item) => {
    return (
      String(item.user?.telegram_id || "") === String(currentTelegramId) &&
      String(item.team?.captain?.telegram_id || "") === String(currentTelegramId) &&
      item.status === "accepted"
    );
  });

  const team = captainMembership?.team || null;

  if (!team) {
    return {
      team: null,
      members: [],
      transferCandidates: [],
    };
  }

  const members = memberships.filter((item) => {
    return Number(item.team?.id) === Number(team.id) && item.status === "accepted";
  });

  const transferCandidates = members.filter((item) => {
    return String(item.user?.telegram_id || "") !== String(currentTelegramId);
  });

  return {
    team,
    members,
    transferCandidates,
  };
}

export function buildCreateTeamBlock() {
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
          <input class="input" name="name" type="text" required />
        </label>

        <label class="field">
          <span class="profile-label">Описание</span>
          <textarea class="input textarea" name="description" required></textarea>
        </label>

        <label class="field">
          <span class="profile-label">Технологический стек</span>
          <input class="input" name="tech_stack" type="text" required />
        </label>

        <label class="field">
          <span class="profile-label">Вакансии</span>
          <input class="input" name="vacancies" type="text" required />
        </label>

        <button class="button primary" type="submit">Создать команду</button>
      </form>
    </section>
  `;
}

export function buildEditProfileBlock(user) {
  return `
    <section class="edit-profile-panel">
      <div class="edit-profile-header">
        <h3>Редактировать профиль</h3>
        <button id="edit-profile-toggle" class="button secondary" type="button">
          Открыть форму
        </button>
      </div>

      <div id="edit-profile-message" class="message hidden"></div>

      <form id="edit-profile-form" class="edit-profile-form hidden">
        <label class="field">
          <span class="profile-label">ФИО</span>
          <input class="input" name="full_name" type="text" value="${escapeHtml(user.full_name || "")}" required />
        </label>

        <label class="field">
          <span class="profile-label">Email</span>
          <input class="input" name="email" type="email" value="${escapeHtml(user.email || "")}" required />
        </label>

        <label class="field">
          <span class="profile-label">Навыки</span>
          <textarea class="input textarea" name="skills" rows="3" required>${escapeHtml(user.skills || "")}</textarea>
        </label>

        <button class="button primary" type="submit">Сохранить профиль</button>
      </form>
    </section>
  `;
}

export function buildLeaveTeamBlock({ membershipInfo }) {
  if (!membershipInfo?.hasAcceptedTeam) return "";

  const isCaptain = Boolean(membershipInfo.isCaptain);

  return `
    <section class="leave-team-panel">
      <div class="leave-team-header">
        <h3>Команда</h3>
      </div>

      <div id="leave-team-message" class="message hidden"></div>

      <div class="muted-box">
        ${isCaptain
          ? "Вы капитан команды. Сначала передайте капитанство или удалите команду."
          : "Вы можете выйти из команды, не меняя профиль."}
      </div>

      <button
        id="leave-team-button"
        class="button secondary"
        type="button"
        ${isCaptain ? "disabled" : ""}
      >
        Выйти из команды
      </button>
    </section>
  `;
}

export function buildCaptainManagementBlock({ team, transferCandidates }) {
  if (!team) return "";

  return `
    <section class="captain-management-panel">
      <div class="captain-management-header">
        <h3>Управление командой</h3>
      </div>

      <div id="captain-management-message" class="message hidden"></div>

      ${
        transferCandidates.length
          ? `
            <label class="field">
              <span class="profile-label">Передать капитанство</span>
              <select id="transfer-captain-select" class="input">
                ${transferCandidates
                  .map(
                    (item) => `
                      <option value="${item.user?.telegram_id}">
                        ${escapeHtml(item.user?.full_name || "Без имени")} — ${escapeHtml(item.user?.skills || "")}
                      </option>
                    `
                  )
                  .join("")}
              </select>
            </label>

            <button id="transfer-captain-button" class="button primary" type="button">
              Передать капитанство
            </button>

            <div class="muted-box" style="margin-top: 12px;">
              Если передавать капитанство некому, команду можно удалить.
            </div>
          `
          : `
            <div class="muted-box">
              В команде нет участников, которым можно передать капитанство.
              Вы можете удалить команду.
            </div>
          `
      }

      <button id="delete-team-button" class="button secondary" type="button">
        Удалить команду
      </button>
    </section>
  `;
}

export function bindCreateTeamActions({ state, loadProfile }) {
  const toggleButton = document.getElementById("create-team-toggle");
  const form = document.getElementById("create-team-form");
  const messageBox = document.getElementById("create-team-message");

  if (!toggleButton || !form || !messageBox) return;

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

    if (!state.currentTelegramId) {
      setMessage("Не удалось определить Telegram ID.", true);
      return;
    }

    const formData = new FormData(form);

    const payload = {
      captain_telegram_id: Number(state.currentTelegramId),
      name: String(formData.get("name") || "").trim(),
      description: String(formData.get("description") || "").trim(),
      tech_stack: String(formData.get("tech_stack") || "").trim(),
      vacancies: String(formData.get("vacancies") || "").trim(),
    };

    if (!payload.name || !payload.description || !payload.tech_stack || !payload.vacancies) {
      setMessage("Заполните все поля.", true);
      return;
    }

    const btn = form.querySelector("button[type='submit']");
    const original = btn.textContent;

    btn.disabled = true;
    btn.textContent = "Создаём...";

    try {
      await request("/api/team/create/", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      setMessage("Команда создана.");
      form.reset();
      form.classList.add("hidden");
      toggleButton.textContent = "Открыть форму";

      await loadProfile();
    } catch (err) {
      setMessage(err.message, true);
    } finally {
      btn.disabled = false;
      btn.textContent = original;
    }
  });
}

export function bindEditProfileActions({ state, loadProfile }) {
  const toggleButton = document.getElementById("edit-profile-toggle");
  const form = document.getElementById("edit-profile-form");
  const messageBox = document.getElementById("edit-profile-message");

  if (!toggleButton || !form || !messageBox) return;

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

    const formData = new FormData(form);

    const payload = {
      telegram_id: Number(state.currentTelegramId),
      full_name: String(formData.get("full_name") || "").trim(),
      email: String(formData.get("email") || "").trim(),
      skills: String(formData.get("skills") || "").trim(),
    };

    if (!payload.full_name || !payload.email || !payload.skills) {
      setMessage("Заполните все поля.", true);
      return;
    }

    const btn = form.querySelector("button[type='submit']");
    const original = btn.textContent;

    btn.disabled = true;
    btn.textContent = "Сохраняем...";

    try {
      await request("/api/profile/update/", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      setMessage("Профиль обновлён.");
      await loadProfile();
    } catch (err) {
      setMessage(err.message, true);
    } finally {
      btn.disabled = false;
      btn.textContent = original;
    }
  });
}

export function bindLeaveTeamActions({ state, loadProfile }) {
  const button = document.getElementById("leave-team-button");
  const messageBox = document.getElementById("leave-team-message");

  if (!button || !messageBox) return;

  const setMessage = (text, isError = false) => {
    messageBox.textContent = text;
    messageBox.classList.remove("hidden", "error", "success");
    messageBox.classList.add(isError ? "error" : "success");
  };

  button.addEventListener("click", async () => {
    if (!state.currentTelegramId) {
      setMessage("Не удалось определить Telegram ID.", true);
      return;
    }

    if (!window.confirm("Вы точно хотите выйти из команды?")) return;

    button.disabled = true;
    button.textContent = "Выходим...";

    try {
      await request("/api/team/leave/", {
        method: "POST",
        body: JSON.stringify({
          user_telegram_id: Number(state.currentTelegramId),
        }),
      });

      setMessage("Вы вышли из команды.");
      await loadProfile();
    } catch (err) {
      setMessage(err.message, true);
    } finally {
      button.disabled = false;
      button.textContent = "Выйти из команды";
    }
  });
}

export function bindDeleteProfileActions({ state, loadProfile }) {
  const button = document.getElementById("delete-profile-button");
  const messageBox = document.getElementById("delete-profile-message");

  if (!button || !messageBox) return;

  const setMessage = (text, isError = false) => {
    messageBox.textContent = text;
    messageBox.classList.remove("hidden", "error", "success");
    messageBox.classList.add(isError ? "error" : "success");
  };

  button.addEventListener("click", async () => {
    if (!state.currentTelegramId) {
      setMessage("Не удалось определить Telegram ID.", true);
      return;
    }

    if (!window.confirm("Удалить профиль полностью? Это действие нельзя отменить.")) return;

    button.disabled = true;
    button.textContent = "Удаляем...";

    try {
      const profileData = await request(`/api/profile/${state.currentTelegramId}/`);
      const user = profileData.user;

      const memberships = await request("/api/team-members/");
      const captainContext = getCaptainContext(memberships, state.currentTelegramId);

      if (captainContext.team) {
        const deleteTeamConfirm = window.confirm(
          "Вы капитан команды. Сначала будет удалена команда, затем профиль. Продолжить?"
        );
        if (!deleteTeamConfirm) {
          return;
        }

        await request("/api/team/delete/", {
          method: "POST",
          body: JSON.stringify({
            captain_telegram_id: Number(state.currentTelegramId),
            team_id: Number(captainContext.team.id),
          }),
        });
      }

      await request("/api/profile/delete/", {
        method: "POST",
        body: JSON.stringify({
          telegram_id: Number(user.telegram_id || state.currentTelegramId),
        }),
      });

      setMessage("Профиль удалён.");

      if (typeof loadProfile === "function") {
        await loadProfile();
      } else {
        loadProfile = null;
      }
    } catch (err) {
      setMessage(err.message, true);
    } finally {
      button.disabled = false;
      button.textContent = "Удалить профиль";
    }
  });
}

export function bindCaptainManagementActions({ state, loadProfile }) {
  const transferButton = document.getElementById("transfer-captain-button");
  const transferSelect = document.getElementById("transfer-captain-select");
  const deleteTeamButton = document.getElementById("delete-team-button");
  const messageBox = document.getElementById("captain-management-message");

  const setMessage = (text, isError = false) => {
    if (!messageBox) return;
    messageBox.textContent = text;
    messageBox.classList.remove("hidden", "error", "success");
    messageBox.classList.add(isError ? "error" : "success");
  };

  if (transferButton && transferSelect) {
    transferButton.addEventListener("click", async () => {
      const newCaptainTelegramId = Number(transferSelect.value);

      if (!state.currentTelegramId || !newCaptainTelegramId) {
        setMessage("Не удалось определить нового капитана.", true);
        return;
      }

      if (!window.confirm("Передать капитанство выбранному участнику?")) return;

      transferButton.disabled = true;
      transferButton.textContent = "Передаём...";

      try {
        const profileData = await request(`/api/profile/${state.currentTelegramId}/`);
        const user = profileData.user;

        const memberships = await request("/api/team-members/");
        const captainMembership = memberships.find((item) => {
          return (
            String(item.user?.telegram_id || "") === String(user.telegram_id) &&
            String(item.team?.captain?.telegram_id || "") === String(user.telegram_id) &&
            item.status === "accepted"
          );
        });

        const teamId = captainMembership?.team?.id;
        if (!teamId) {
          setMessage("Не удалось определить команду.", true);
          return;
        }

        await request("/api/team/transfer-captain/", {
          method: "POST",
          body: JSON.stringify({
            captain_telegram_id: Number(state.currentTelegramId),
            team_id: Number(teamId),
            new_captain_telegram_id: newCaptainTelegramId,
          }),
        });

        setMessage("Капитанство передано.");
        await loadProfile();
      } catch (err) {
        setMessage(err.message, true);
      } finally {
        transferButton.disabled = false;
        transferButton.textContent = "Передать капитанство";
      }
    });
  }

  if (deleteTeamButton) {
    deleteTeamButton.addEventListener("click", async () => {
      if (!state.currentTelegramId) {
        setMessage("Не удалось определить Telegram ID.", true);
        return;
      }

      if (!window.confirm("Удалить команду? Это действие нельзя отменить.")) return;

      deleteTeamButton.disabled = true;
      deleteTeamButton.textContent = "Удаляем...";

      try {
        const profileData = await request(`/api/profile/${state.currentTelegramId}/`);
        const user = profileData.user;

        const memberships = await request("/api/team-members/");
        const captainMembership = memberships.find((item) => {
          return (
            String(item.user?.telegram_id || "") === String(user.telegram_id) &&
            String(item.team?.captain?.telegram_id || "") === String(user.telegram_id) &&
            item.status === "accepted"
          );
        });

        const teamId = captainMembership?.team?.id;
        if (!teamId) {
          setMessage("Не удалось определить команду.", true);
          return;
        }

        await request("/api/team/delete/", {
          method: "POST",
          body: JSON.stringify({
            captain_telegram_id: Number(state.currentTelegramId),
            team_id: Number(teamId),
          }),
        });

        setMessage("Команда удалена.");
        await loadProfile();
      } catch (err) {
        setMessage(err.message, true);
      } finally {
        deleteTeamButton.disabled = false;
        deleteTeamButton.textContent = "Удалить команду";
      }
    });
  }
}

export async function loadProfile({ state, els }) {
  const { profileContent, messageBox } = els;

  showScreen("profile-screen", els.screens, () => clearMessage(messageBox));

  if (!state.currentTelegramId) {
    profileContent.textContent = "Не удалось определить Telegram ID";
    return;
  }

  profileContent.textContent = "Загрузка профиля...";

  try {
    const profileData = await request(`/api/profile/${state.currentTelegramId}/`);
    const user = profileData.user;

    let membershipInfo = {
      statusText: "Неизвестно",
      teamName: "—",
      isCaptain: false,
      hasAcceptedTeam: false,
    };

    let createTeamHtml = "";
    let leaveTeamHtml = "";
    let captainManagementHtml = "";

    try {
      const membershipData = await request("/api/team-members/");
      membershipInfo = getMembershipInfo(membershipData, state.currentTelegramId);

      if (!membershipInfo.hasAcceptedTeam && user.is_kaptain) {
        createTeamHtml = buildCreateTeamBlock();
      }

      if (membershipInfo.hasAcceptedTeam) {
        leaveTeamHtml = buildLeaveTeamBlock({ membershipInfo });
      }

      if (membershipInfo.isCaptain) {
        const captainContext = getCaptainContext(membershipData, state.currentTelegramId);
        captainManagementHtml = buildCaptainManagementBlock({
          team: captainContext.team,
          transferCandidates: captainContext.transferCandidates,
        });
      }
    } catch {
      // ignore
    }

    const captainButton = document.getElementById("captain-button");
    if (captainButton) {
      captainButton.classList.toggle("hidden", !(user.is_kaptain || user.role === "CAPTAIN"));
    }

    if (els.captainDashboard && !captainButton?.classList.contains("hidden")) {
      els.captainDashboard.classList.add("hidden");
    }

    profileContent.innerHTML = `
      <div class="profile-card">
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

        <div class="profile-row">
          <span class="profile-label">Статус</span>
          <strong>${escapeHtml(membershipInfo.statusText)}</strong>
        </div>

        <div class="profile-row">
          <span class="profile-label">Команда</span>
          <strong>${escapeHtml(membershipInfo.teamName)}</strong>
        </div>

        <section class="edit-profile-panel">
          <div class="edit-profile-header">
            <h3>Редактировать профиль</h3>
            <button id="edit-profile-toggle" class="button secondary" type="button">Открыть форму</button>
          </div>

          <div id="edit-profile-message" class="message hidden"></div>

          <form id="edit-profile-form" class="edit-profile-form hidden">
            <label class="field">
              <span class="profile-label">ФИО</span>
              <input class="input" name="full_name" type="text" value="${escapeHtml(user.full_name || "")}" required />
            </label>

            <label class="field">
              <span class="profile-label">Email</span>
              <input class="input" name="email" type="email" value="${escapeHtml(user.email || "")}" required />
            </label>

            <label class="field">
              <span class="profile-label">Навыки</span>
              <textarea class="input textarea" name="skills" rows="3" required>${escapeHtml(user.skills || "")}</textarea>
            </label>

            <button class="button primary" type="submit">Сохранить профиль</button>
          </form>
        </section>

        ${leaveTeamHtml}
        ${createTeamHtml}
        ${captainManagementHtml}

        <section class="delete-profile-panel">
          <div class="delete-profile-header">
            <h3>Удаление профиля</h3>
          </div>

          <div id="delete-profile-message" class="message hidden"></div>

          <button id="delete-profile-button" class="button secondary" type="button">
            Удалить профиль
          </button>
        </section>
      </div>
    `;

    bindEditProfileActions({
      state,
      loadProfile: () => loadProfile({ state, els }),
    });

    bindCreateTeamActions({
      state,
      loadProfile: () => loadProfile({ state, els }),
    });

    bindLeaveTeamActions({
      state,
      loadProfile: () => loadProfile({ state, els }),
    });

    bindDeleteProfileActions({
      state,
      loadProfile: () => loadProfile({ state, els }),
    });

    bindCaptainManagementActions({
      state,
      loadProfile: () => loadProfile({ state, els }),
    });
  } catch (error) {
    profileContent.textContent =
      error.message === "User not found."
        ? "Сначала зарегистрируйтесь через бота"
        : error.message;
  }
}