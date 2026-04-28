import { request } from "./api.js";
import { clearMessage, escapeHtml, showScreen } from "./utils.js";

export async function syncOrganizerButton({ state }) {
  const btn = document.getElementById("organizer-button");
  if (!btn || !state.currentTelegramId) {
    return;
  }
  try {
    const perm = await request(
      `/api/hackathons/permissions/?telegram_id=${encodeURIComponent(state.currentTelegramId)}`
    );
    btn.classList.toggle("hidden", !perm.can_create_hackathon);
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
      <label class="field row-inline">
        <input id="hackathon-join-open" type="checkbox" name="is_team_join_open" checked />
        <span class="profile-label">Капитаны могут подключать команды</span>
      </label>
      <button class="button primary" type="submit">Создать</button>
    </form>
    <div id="organizer-form-message" class="message hidden"></div>
  `;
}

export async function loadOrganizerScreen({ state, els }) {
  showScreen("organizer-screen", els.screens, () => clearMessage(els.messageBox));

  const root = document.getElementById("organizer-content");
  if (!root) {
    return;
  }
  if (!state.currentTelegramId) {
    root.innerHTML = "<p class=\"muted\">Нет Telegram ID.</p>";
    return;
  }

  root.innerHTML = "<p class=\"muted\">Загрузка…</p>";

  let perm;
  try {
    perm = await request(
      `/api/hackathons/permissions/?telegram_id=${encodeURIComponent(state.currentTelegramId)}`
    );
  } catch (e) {
    root.innerHTML = `<div class="card error-block"><p>${escapeHtml(e.message)}</p></div>`;
    return;
  }

  if (!perm.can_create_hackathon) {
    root.innerHTML = `
      <div class="muted-box">
        <p><strong>Создание хакатонов недоступно</strong></p>
        <p class="muted">Варианты:</p>
        <ul class="muted">
          <li>В <code>.env</code> задайте <code>ORGANIZER_BOOTSTRAP_TELEGRAM_IDS</code> вашим числовым Telegram ID и перезапустите Django.</li>
          <li>Или в Django Admin откройте существующий Hackathon и добавьте вашего пользователя в «организаторы» — тогда создавать новые события можно будет и без bootstrap.</li>
        </ul>
      </div>`;
    return;
  }

  root.innerHTML = buildCreateForm();

  const form = document.getElementById("create-hackathon-form");
  const msg = document.getElementById("organizer-form-message");
  if (!form) {
    return;
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const fd = new FormData(form);
    const name = String(fd.get("name") || "").trim();
    const description = String(fd.get("description") || "").trim();
    const schedule_sheet_url = String(fd.get("schedule_sheet_url") || "").trim();
    const is_team_join_open = document.getElementById("hackathon-join-open")?.checked ?? true;

    if (!name) {
      if (msg) {
        msg.textContent = "Укажите название.";
        msg.classList.remove("hidden");
        msg.classList.add("error");
      }
      return;
    }

    const submitBtn = form.querySelector("button[type='submit']");
    submitBtn.disabled = true;
    if (msg) {
      msg.classList.add("hidden");
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
      document.getElementById("hackathon-join-open").checked = true;
      if (msg) {
        msg.textContent = `Создано: ${h.name || ""} (slug: ${h.slug || ""}, id: ${h.id || ""})`;
        msg.classList.remove("hidden", "error");
      }
      await syncOrganizerButton({ state });
    } catch (e) {
      if (msg) {
        msg.textContent = e.message;
        msg.classList.remove("hidden");
        msg.classList.add("error");
      }
    } finally {
      submitBtn.disabled = false;
    }
  });
}
