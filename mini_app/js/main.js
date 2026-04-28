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

async function syncRoleUI() {
  if (!state.currentTelegramId) return;

  await syncCaptainButtonVisibility({ state, els });
  await syncOrganizerButton({ state });
}

function init() {
  state.currentTelegramId = getTelegramId();

  const profileButton = document.getElementById("profile-button");
  const teamsButton = document.getElementById("teams-button");
  const captainButton = document.getElementById("captain-button");
  const organizerButton = document.getElementById("organizer-button");

  // --- PROFILE ---
  profileButton?.addEventListener("click", async () => {
    clearMessage(els.messageBox);
    await loadProfile({ state, els });
    await syncRoleUI();
  });

  // --- TEAMS ---
  teamsButton?.addEventListener("click", async () => {
    clearMessage(els.messageBox);
    await loadTeams({ state, els });
    await syncRoleUI();
  });

  // --- ORGANIZER ---
  organizerButton?.addEventListener("click", async () => {
    clearMessage(els.messageBox);
    await loadOrganizerScreen({ state, els });
  });

  // --- CAPTAIN PANEL ---
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

  // --- FILTERS ---
  els.teamSearchInput?.addEventListener("input", () => applyFilters(state, els));
  els.techStackFilter?.addEventListener("change", () => applyFilters(state, els));

  // --- SCREEN NAV ---
  document.querySelectorAll("[data-screen]").forEach((button) => {
    button.addEventListener("click", async () => {
      showScreen(button.dataset.screen, screens, () =>
        clearMessage(els.messageBox)
      );
      await syncRoleUI();
    });
  });

  // --- TELEGRAM INIT ---
  if (tg) {
    tg.ready();
    tg.expand();
  } else if (els.devHint) {
    els.devHint.classList.remove("hidden");
    els.devHint.textContent =
      "Локально: добавь ?api_base=http://127.0.0.1:8000&telegram_id=... в URL";
  }

  // --- INITIAL SYNC ---
  if (state.currentTelegramId) {
    void syncRoleUI();
  }
}

init();