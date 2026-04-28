import { getTelegramId } from "./api.js";
import { clearMessage, showScreen } from "./utils.js";
import { loadProfile } from "./profile.js";
import { loadCaptainDashboard, syncCaptainButtonVisibility } from "./captain.js";
import { syncOrganizerButton, loadOrganizerScreen } from "./organizer.js";
import { loadTeams, applyFilters } from "./teams.js";

const tg = window.Telegram?.WebApp;

const state = {
  currentTelegramId: null,
  allTeams: [],
};

const screens = {
  home: document.getElementById("home-screen"),
  profile: document.getElementById("profile-screen"),
  teams: document.getElementById("teams-screen"),
};

const els = {
  screens,
  profileContent: document.getElementById("profile-content"),
  teamsList: document.getElementById("teams-list"),
  messageBox: document.getElementById("message"),
  devHint: document.getElementById("dev-hint"),
  teamSearchInput: document.getElementById("team-search"),
  techStackFilter: document.getElementById("tech-stack-filter"),
  captainDashboard: document.getElementById("captain-dashboard"),
};

function init() {
  state.currentTelegramId = getTelegramId();

  const profileButton = document.getElementById("profile-button");
  const teamsButton = document.getElementById("teams-button");
  const captainButton = document.getElementById("captain-button");

  profileButton?.addEventListener("click", () => {
    clearMessage(els.messageBox);
    loadProfile({ state, els });
  });

  teamsButton?.addEventListener("click", () => {
    clearMessage(els.messageBox);
    loadTeams({ state, els });
  });

  document.getElementById("organizer-button")?.addEventListener("click", () => {
    clearMessage(els.messageBox);
    loadOrganizerScreen({ state, els });
  });

  captainButton?.addEventListener("click", async () => {
    if (!els.captainDashboard) return;

    const isHidden = els.captainDashboard.classList.contains("hidden");

    if (isHidden) {
      els.captainDashboard.classList.remove("hidden");
      await loadCaptainDashboard({ state, els });
    } else {
      els.captainDashboard.classList.add("hidden");
    }
  });

  els.teamSearchInput?.addEventListener("input", () => applyFilters(state, els));
  els.techStackFilter?.addEventListener("change", () => applyFilters(state, els));

  document.querySelectorAll("[data-screen]").forEach((button) => {
    button.addEventListener("click", () =>
      showScreen(button.dataset.screen, screens, () => clearMessage(els.messageBox))
    );
  });

  if (tg) {
    tg.ready();
    tg.expand();
  } else if (els.devHint) {
    els.devHint.classList.remove("hidden");
    els.devHint.textContent =
      "Локально: укажите ?api_base=http://127.0.0.1:8000 и ?telegram_id=… при открытии index.html с диска (Django должен быть запущен).";
  }

  if (state.currentTelegramId) {
    syncCaptainButtonVisibility({ state, els });
    void syncOrganizerButton({ state });
  }
}

init();