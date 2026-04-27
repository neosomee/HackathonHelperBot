import { request } from "./api.js";
import {
  clearMessage,
  escapeHtml,
  getMembershipInfo,
  showScreen,
} from "./utils.js";

import {
  bindEditProfile,
  bindDeleteProfile,
  bindLeaveTeam
} from "./updateProfile.js";

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

    try {
      const membershipData = await request("/api/team-members/");
      membershipInfo = getMembershipInfo(membershipData, state.currentTelegramId);

      if (!membershipInfo.hasAcceptedTeam && user.is_kaptain) {
        createTeamHtml = buildCreateTeamBlock();
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

        ${createTeamHtml}
      </div>
    `;

    bindCreateTeamActions({
      state,
      loadProfile: () => loadProfile({ state, els }),
    });
  } catch (error) {
    profileContent.textContent =
      error.message === "User not found."
        ? "Сначала зарегистрируйтесь через бота"
        : error.message;
  }

      bindEditProfile({
      state,
      reload: () => loadProfile({ state, els }),
    });

    bindDeleteProfile({
      state,
      onDeleted: () => {
        els.profileContent.innerHTML = "Профиль удалён";
      },
    });

    bindLeaveTeam({
      state,
      reload: () => loadProfile({ state, els }),
    });
}