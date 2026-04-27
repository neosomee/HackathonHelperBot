import { request } from "./api.js";
import { escapeHtml, showMessage } from "./utils.js";

export async function loadTeams({ state, els }) {
  const { screens, teamsList, teamSearchInput, techStackFilter, messageBox } = els;

  Object.values(screens).forEach((screen) => screen.classList.remove("active"));
  screens.teams.classList.add("active");

  teamsList.innerHTML = '<div class="panel muted">Загрузка команд...</div>';

  try {
    const data = await request("/api/team/list/");
    state.allTeams = data.teams || [];
    renderTechStackOptions(state.allTeams, techStackFilter);
    applyFilters(state, els);
  } catch (error) {
    teamsList.innerHTML = "";
    showMessage(messageBox, error.message, true);
  }
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

  [...values].sort((a, b) => a.localeCompare(b, "ru")).forEach((value) => {
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

  renderTeams(filteredTeams, els);
}

function renderTeams(teams, els) {
  if (!teams.length) {
    els.teamsList.innerHTML = '<div class="panel muted">Команды по текущему фильтру не найдены.</div>';
    return;
  }

  els.teamsList.innerHTML = teams
    .map(
      (team) => `
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
    `
    )
    .join("");

  document.querySelectorAll("[data-team-id]").forEach((button) => {
    button.addEventListener("click", () => applyToTeam(state, button, els));
  });
}

async function applyToTeam(state, button, els) {
  if (!state.currentTelegramId) {
    showMessage(els.messageBox, "Откройте Mini App из Telegram, чтобы отправить отклик.", true);
    return;
  }

  const teamId = Number(button.dataset.teamId);
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
  } catch (error) {
    button.disabled = false;
    button.textContent = "Откликнуться";
    showMessage(els.messageBox, error.message, true);
  }
}