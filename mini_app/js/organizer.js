import { request } from "./api.js";
import { clearMessage, escapeHtml, showScreen } from "./utils.js";

export async function syncOrganizerButton({ state }) {
  const btn = document.getElementById("organizer-button");
  if (!btn || !state.currentTelegramId) return;

  try {
    const perm = await request(
      `/api/hackathons/permissions/?telegram_id=${encodeURIComponent(state.currentTelegramId)}`
    );

    const canSeeOrganizer =
      Boolean(perm.can_create_hackathon) ||
      Boolean(perm.is_organizer) ||
      Number(perm.organized_count || 0) > 0;

    btn.classList.toggle("hidden", !canSeeOrganizer);
  } catch {
    btn.classList.add("hidden");
  }
}

function buildCreateForm() {
  return `
    <div class="muted-box">
      <p><strong>Создать хакатон</strong></p>
      <p class="muted">После создания вы автоматически становитесь организатором события.</p>
    </div>

    <form id="create-hackathon-form" class="create-team-form">
      <label class="field">
        <span class="profile-label">Название</span>
        <input class="input" name="name" type="text" required maxlength="255" />
      </label>

      <label class="field">
        <span class="profile-label">Описание</span>
        <textarea class="input textarea" name="description" rows="3"></textarea>
      </label>

      <label class="field">
        <span class="profile-label">Ссылка на Google Таблицу (расписание)</span>
        <input class="input" name="schedule_sheet_url" type="url" placeholder="https://..." />
      </label>

      <div class="field">
        <span class="profile-label">Подключение команд</span>
        <label class="inline-checkbox">
          <input
            id="hackathon-join-open"
            type="checkbox"
            name="is_team_join_open"
            checked
            class="inline-checkbox-input"
          />
          <span class="inline-checkbox-text">Капитаны могут подключать команды к этому хакатону</span>
        </label>
      </div>

      <button class="button primary" type="submit">Создать</button>
    </form>

    <div id="organizer-form-message" class="message hidden"></div>
  `;
}

function buildHackathonCard(h) {
  return `
    <article class="muted-box organizer-card" data-hackathon-id="${h.id}">
      <div class="organizer-card-head">
        <strong>${escapeHtml(h.name || "")}</strong>
        <span class="muted">${h.is_team_join_open ? "Набор открыт" : "Набор закрыт"}</span>
      </div>

      ${h.description ? `<p class="muted">${escapeHtml(h.description)}</p>` : ""}
      ${
        h.schedule_sheet_url
          ? `<div><a class="link-like" href="${escapeHtml(h.schedule_sheet_url)}" target="_blank" rel="noopener noreferrer">Расписание (Google Таблица)</a></div>`
          : ""
      }

      <div class="organizer-card-actions">
        <button type="button" class="button secondary organizer-open-btn" data-action="open" data-hackathon-id="${h.id}">
          Открыть
        </button>
        <button type="button" class="button secondary organizer-edit-btn" data-action="edit" data-hackathon-id="${h.id}">
          Редактировать
        </button>
        <button type="button" class="button secondary organizer-delete-btn" data-action="delete" data-hackathon-id="${h.id}">
          Удалить
        </button>
      </div>
    </article>
  `;
}

function buildHackathonEditForm(h) {
  return `
    <section class="muted-box organizer-editor" data-hackathon-id="${h.id}">
      <div class="organizer-card-head">
        <strong>Панель хакатона</strong>
        <span class="muted">ID: ${h.id}</span>
      </div>

      <form id="hackathon-edit-form" class="create-team-form">
        <label class="field">
          <span class="profile-label">Название</span>
          <input class="input" name="name" type="text" required maxlength="255" value="${escapeHtml(h.name || "")}" />
        </label>

        <label class="field">
          <span class="profile-label">Описание</span>
          <textarea class="input textarea" name="description" rows="3">${escapeHtml(h.description || "")}</textarea>
        </label>

        <label class="field">
          <span class="profile-label">Ссылка на Google Таблицу (расписание)</span>
          <input
            class="input"
            name="schedule_sheet_url"
            type="url"
            value="${escapeHtml(h.schedule_sheet_url || "")}"
            placeholder="https://..."
          />
        </label>

        <div class="field">
          <span class="profile-label">Подключение команд</span>
          <label class="inline-checkbox">
            <input
              id="hackathon-edit-join-open"
              type="checkbox"
              name="is_team_join_open"
              ${h.is_team_join_open ? "checked" : ""}
              class="inline-checkbox-input"
            />
            <span class="inline-checkbox-text">Капитаны могут подключать команды к этому хакатону</span>
          </label>
        </div>

        <button class="button primary" type="submit">Сохранить</button>
      </form>

      <div id="organizer-edit-message" class="message hidden"></div>
    </section>
  `;
}

function buildOrganizerScreen({ perm, hackathons }) {
  const hasAccess =
    Boolean(perm.can_create_hackathon) ||
    Boolean(perm.is_organizer) ||
    Number(perm.organized_count || 0) > 0;

  if (!hasAccess) {
    return `
      <div class="muted-box">
        <p><strong>Доступ к панели организатора недоступен</strong></p>
        <p class="muted">Добавьте пользователя в organizers у нужного хакатона через Django Admin.</p>
      </div>
    `;
  }

  return `
    <div class="organizer-page">
      <section class="organizer-section">
        ${buildCreateForm()}
      </section>

      <section class="organizer-section">
        <div class="muted-box">
          <p><strong>Мои хакатоны</strong></p>
          <p class="muted">Хакатоны, где вы назначены организатором.</p>
        </div>

        <div id="organized-hackathons-list" class="organizer-list">
          ${
            hackathons.length
              ? hackathons.map(buildHackathonCard).join("")
              : `<div class="muted-box">Пока нет доступных хакатонов.</div>`
          }
        </div>
      </section>

      <section class="organizer-section">
        <div id="organizer-editor-container" class="organizer-editor-container">
          <div class="muted-box">Выберите хакатон, чтобы открыть панель управления.</div>
        </div>
      </section>
    </div>
  `;
}

async function fetchOrganizerAccess(state) {
  return request(
    `/api/hackathons/permissions/?telegram_id=${encodeURIComponent(state.currentTelegramId)}`
  );
}

async function fetchOrganizedHackathons(state) {
  const res = await request(
    `/api/hackathons/organized/?telegram_id=${encodeURIComponent(state.currentTelegramId)}`
  );
  return res.hackathons || [];
}

async function fetchHackathonDetail(state, hackathonId) {
  return request(
    `/api/hackathons/${hackathonId}/?telegram_id=${encodeURIComponent(state.currentTelegramId)}`
  );
}

function bindCreateForm(state, els) {
  const form = document.getElementById("create-hackathon-form");
  const msg = document.getElementById("organizer-form-message");
  if (!form) return;

  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const fd = new FormData(form);
    const name = String(fd.get("name") || "").trim();
    const description = String(fd.get("description") || "").trim();
    const schedule_sheet_url = String(fd.get("schedule_sheet_url") || "").trim();
    const is_team_join_open =
      document.getElementById("hackathon-join-open")?.checked ?? true;

    if (!name) {
      if (msg) {
        msg.textContent = "Укажите название.";
        msg.classList.remove("hidden");
        msg.classList.add("error");
      }
      return;
    }

    const submitBtn = form.querySelector("button[type='submit']");
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = "Создаём...";
    }

    if (msg) {
      msg.classList.add("hidden");
      msg.classList.remove("error");
    }

    try {
      const data = await request("/api/hackathons/create/", {
        method: "POST",
        body: JSON.stringify({
          telegram_id: Number(state.currentTelegramId),
          name,
          description,
          schedule_sheet_url,
          is_team_join_open,
        }),
      });

      const h = data.hackathon || {};
      form.reset();

      const joinOpen = document.getElementById("hackathon-join-open");
      if (joinOpen) joinOpen.checked = true;

      if (msg) {
        msg.textContent = `Создано: ${h.name || ""} (slug: ${h.slug || ""}, id: ${h.id || ""})`;
        msg.classList.remove("hidden", "error");
      }

      await loadOrganizerScreen({ state, els });
      await syncOrganizerButton({ state });
    } catch (e) {
      if (msg) {
        msg.textContent = e.message;
        msg.classList.remove("hidden");
        msg.classList.add("error");
      }
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = "Создать";
      }
    }
  });
}

function bindOrganizerListActions(state, els) {
  const list = document.getElementById("organized-hackathons-list");
  const editor = document.getElementById("organizer-editor-container");
  if (!list || !editor) return;

  list.addEventListener("click", async (event) => {
    const target = event.target.closest("button[data-action]");
    if (!target) return;

    const action = target.dataset.action;
    const hackathonId = Number(target.dataset.hackathonId);
    if (!hackathonId) return;

    if (action === "open" || action === "edit") {
      editor.innerHTML = `<div class="muted-box">Загрузка панели...</div>`;

      try {
        const data = await fetchHackathonDetail(state, hackathonId);
        const h = data.hackathon || {};

        editor.innerHTML = buildHackathonEditForm(h);
        bindHackathonEditForm(state, els, hackathonId);
      } catch (e) {
        editor.innerHTML = `<div class="card error-block"><p>${escapeHtml(e.message)}</p></div>`;
      }

      return;
    }

    if (action === "delete") {
      const ok = window.confirm("Удалить хакатон? Это действие нельзя отменить.");
      if (!ok) return;

      target.disabled = true;
      const originalText = target.textContent;
      target.textContent = "Удаляем...";

      try {
        await request(`/api/hackathons/${hackathonId}/delete/`, {
          method: "DELETE",
          body: JSON.stringify({
            telegram_id: Number(state.currentTelegramId),
          }),
        });

        await loadOrganizerScreen({ state, els });
      } catch (e) {
        target.disabled = false;
        target.textContent = originalText;
        editor.innerHTML = `<div class="card error-block"><p>${escapeHtml(e.message)}</p></div>`;
      }
    }
  });
}

function bindHackathonEditForm(state, els, hackathonId) {
  const form = document.getElementById("hackathon-edit-form");
  const msg = document.getElementById("organizer-edit-message");
  if (!form) return;

  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const fd = new FormData(form);
    const name = String(fd.get("name") || "").trim();
    const description = String(fd.get("description") || "").trim();
    const schedule_sheet_url = String(fd.get("schedule_sheet_url") || "").trim();
    const is_team_join_open =
      document.getElementById("hackathon-edit-join-open")?.checked ?? true;

    if (!name) {
      if (msg) {
        msg.textContent = "Укажите название.";
        msg.classList.remove("hidden");
        msg.classList.add("error");
      }
      return;
    }

    const submitBtn = form.querySelector("button[type='submit']");
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = "Сохраняем...";
    }

    if (msg) {
      msg.classList.add("hidden");
      msg.classList.remove("error");
    }

    try {
      await request(`/api/hackathons/${hackathonId}/update/`, {
        method: "PATCH",
        body: JSON.stringify({
          telegram_id: Number(state.currentTelegramId),
          name,
          description,
          schedule_sheet_url,
          is_team_join_open,
        }),
      });

      if (msg) {
        msg.textContent = "Хакатон обновлён.";
        msg.classList.remove("hidden", "error");
      }

      await loadOrganizerScreen({ state, els });
    } catch (e) {
      if (msg) {
        msg.textContent = e.message;
        msg.classList.remove("hidden");
        msg.classList.add("error");
      }
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = "Сохранить";
      }
    }
  });
}

export async function loadOrganizerScreen({ state, els }) {
  showScreen("organizer-screen", els.screens, () => clearMessage(els.messageBox));

  const root = document.getElementById("organizer-content");
  if (!root) return;

  if (!state.currentTelegramId) {
    root.innerHTML = '<p class="muted">Нет Telegram ID.</p>';
    return;
  }

  root.innerHTML = '<p class="muted">Загрузка…</p>';

  let perm;
  let hackathons = [];

  try {
    perm = await fetchOrganizerAccess(state);
  } catch (e) {
    root.innerHTML = `<div class="card error-block"><p>${escapeHtml(e.message)}</p></div>`;
    return;
  }

  try {
    hackathons = await fetchOrganizedHackathons(state);
  } catch {
    hackathons = [];
  }

  root.innerHTML = buildOrganizerScreen({ perm, hackathons });

  const hasAccess =
    Boolean(perm.can_create_hackathon) ||
    Boolean(perm.is_organizer) ||
    Number(perm.organized_count || 0) > 0;

  if (!hasAccess) {
    return;
  }

  bindCreateForm(state, els);
  bindOrganizerListActions(state, els);
}