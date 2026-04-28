import { request } from "./api.js";
import { escapeHtml, showMessage } from "./utils.js";

export async function loadTeams({ state, els }) {
  const { screens, teamsList, teamSearchInput, techStackFilter, messageBox } = els;

  Object.values(screens).forEach((screen) => screen.classList.remove("active"));
  screens.teams.classList.add("active");

  teamsList.innerHTML = '<div class="panel muted">Загрузка команд...</div>';

  try {
    const [teamsResponse, membershipsResponse] = await Promise.all([
      request("/api/team/list/"),
      state.currentTelegramId ? request("/api/team-members/") : Promise.resolve([]),
    ]);

    state.allTeams = teamsResponse.teams || [];
    state.teamMembershipInfo = getCurrentUserMembershipInfo(
      membershipsResponse,
      state.currentTelegramId
    );

    renderTechStackOptions(state.allTeams, techStackFilter);
    applyFilters(state, els);
  } catch (error) {
    teamsList.innerHTML = "";
    showMessage(messageBox, error.message, true);
  }
}

function getCurrentUserMembershipInfo(membershipData, telegramId) {
  const memberships = Array.isArray(membershipData) ? membershipData : [];

  const userMemberships = memberships.filter((item) => {
    return String(item.user?.telegram_id || "") === String(telegramId);
  });

  const acceptedMembership = userMemberships.find((item) => item.status === "accepted");
  if (acceptedMembership) {
    return {
      hasAcceptedTeam: true,
      hasPendingApplication: false,
      teamName: acceptedMembership.team?.name || "Без названия",
      teamId: acceptedMembership.team?.id || null,
    };
  }

  const pendingMembership = userMemberships.find((item) => item.status === "pending");
  if (pendingMembership) {
    return {
      hasAcceptedTeam: false,
      hasPendingApplication: true,
      teamName: pendingMembership.team?.name || "Без названия",
      teamId: pendingMembership.team?.id || null,
    };
  }

  return {
    hasAcceptedTeam: false,
    hasPendingApplication: false,
    teamName: null,
    teamId: null,
  };
}

function renderTechStackOptions(teams, techStackFilter) {
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

  [...values]
    .sort((a, b) => a.localeCompare(b, "ru"))
    .forEach((value) => {
      techStackFilter.insertAdjacentHTML(
        "beforeend",
        `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`
      );
    });

  techStackFilter.value = currentValue;
}

export function applyFilters(state, els) {
  const searchText = els.teamSearchInput.value.trim().toLowerCase();
  const techStackValue = els.techStackFilter.value.trim().toLowerCase();

  const filteredTeams = state.allTeams.filter((team) => {
    const haystack = [team.name, team.description, team.tech_stack, team.vacancies]
      .join(" ")
      .toLowerCase();

    const matchesText = !searchText || haystack.includes(searchText);
    const matchesTechStack =
      !techStackValue || String(team.tech_stack || "").toLowerCase().includes(techStackValue);

    return matchesText && matchesTechStack;
  });

  renderTeams(filteredTeams, state, els);
}

function renderTeams(teams, state, els) {
  if (!teams.length) {
    els.teamsList.innerHTML = '<div class="panel muted">Команды по текущему фильтру не найдены.</div>';
    return;
  }

  const membershipInfo = state.teamMembershipInfo || {
    hasAcceptedTeam: false,
    hasPendingApplication: false,
    teamName: null,
    teamId: null,
  };

  els.teamsList.innerHTML = teams
    .map((team) => {
      const isClosed = !team.is_open;
      const isCurrentTeam = Number(membershipInfo.teamId) === Number(team.id);

      let buttonText = "Откликнуться";
      let disabled = "";

      if (isClosed) {
        buttonText = "Набор закрыт";
        disabled = "disabled";
      } else if (membershipInfo.hasAcceptedTeam) {
        buttonText = isCurrentTeam ? "Ваша команда" : "Вы уже в команде";
        disabled = "disabled";
      } else if (membershipInfo.hasPendingApplication && isCurrentTeam) {
        buttonText = "Заявка отправлена";
        disabled = "disabled";
      }

      return `
        <article class="team-card">
          <h3>${escapeHtml(team.name)}</h3>
          <p class="muted">${escapeHtml(team.description)}</p>
          <div class="team-meta">
            <div class="team-field"><strong>Стек:</strong> ${escapeHtml(team.tech_stack)}</div>
            <div class="team-field"><strong>Вакансии:</strong> ${escapeHtml(team.vacancies)}</div>
            <div><span class="status">${team.is_open ? "Набор открыт" : "Набор закрыт"}</span></div>
          </div>
          <button
            class="button primary apply-team-button"
            type="button"
            data-team-id="${team.id}"
            ${disabled}
          >
            ${buttonText}
          </button>
        </article>
      `;
    })
    .join("");

  document.querySelectorAll(".apply-team-button").forEach((button) => {
    button.addEventListener("click", () => applyToTeam(state, button, els));
  });
}

async function applyToTeam(state, button, els) {
  if (!state.currentTelegramId) {
    showMessage(els.messageBox, "Откройте Mini App из Telegram, чтобы отправить отклик.", true);
    return;
  }

  const membershipInfo = state.teamMembershipInfo || {
    hasAcceptedTeam: false,
    hasPendingApplication: false,
    teamId: null,
    teamName: null,
  };

  const teamId = Number(button.dataset.teamId);

  if (membershipInfo.hasAcceptedTeam) {
    showMessage(
      els.messageBox,
      `Вы уже состоите в команде${membershipInfo.teamName ? `: ${membershipInfo.teamName}` : ""}.`,
      true
    );
    return;
  }

  if (membershipInfo.hasPendingApplication && Number(membershipInfo.teamId) === teamId) {
    showMessage(
      els.messageBox,
      `Заявка в команду${membershipInfo.teamName ? ` «${membershipInfo.teamName}»` : ""} уже отправлена.`,
      true
    );
    return;
  }

  button.disabled = true;
  button.textContent = "Отправляем...";

  try {
    await request("/api/team/apply/", {
      method: "POST",
      body: JSON.stringify({
        user_telegram_id: Number(state.currentTelegramId),
        team_id: teamId,
      }),
    });

    button.textContent = "Заявка отправлена";
    showMessage(els.messageBox, "Заявка отправлена");

    state.teamMembershipInfo = {
      hasAcceptedTeam: false,
      hasPendingApplication: true,
      teamName: button.closest(".team-card")?.querySelector("h3")?.textContent || null,
      teamId,
    };

    applyFilters(state, els);
  } catch (error) {
    button.disabled = false;
    button.textContent = "Откликнуться";
    showMessage(els.messageBox, error.message, true);
  }
}