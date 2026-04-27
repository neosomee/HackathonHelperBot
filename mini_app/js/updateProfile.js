// updateProfile.js
import { request } from "./api.js";

/* =========================
   EDIT PROFILE
========================= */
export function bindEditProfile({ state, reload }) {
  const form = document.getElementById("edit-profile-form");
  const msg = document.getElementById("edit-profile-message");
  const toggle = document.getElementById("edit-profile-toggle");

  if (!form || !msg || !toggle) return;

  toggle.onclick = () => {
    form.classList.toggle("hidden");
  };

  form.onsubmit = async (e) => {
    e.preventDefault();

    const data = new FormData(form);

    const payload = {
      telegram_id: Number(state.currentTelegramId),
      full_name: data.get("full_name"),
      email: data.get("email"),
      skills: data.get("skills"),
    };

    try {
      await request("/api/profile/update/", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      msg.textContent = "Профиль обновлён";
      msg.classList.remove("hidden");
      reload();

    } catch (err) {
      msg.textContent = err.message;
      msg.classList.remove("hidden");
      msg.classList.add("error");
    }
  };
}

/* =========================
   DELETE PROFILE
========================= */
export function bindDeleteProfile({ state, onDeleted }) {
  const btn = document.getElementById("delete-profile-button");

  if (!btn) return;

  btn.onclick = async () => {
    if (!confirm("Удалить профиль?")) return;

    try {
      await request("/api/profile/delete/", {
        method: "POST",
        body: JSON.stringify({
          telegram_id: Number(state.currentTelegramId),
        }),
      });

      onDeleted();

    } catch (err) {
      alert(err.message);
    }
  };
}

/* =========================
   LEAVE TEAM
========================= */
export function bindLeaveTeam({ state, reload }) {
  const btn = document.getElementById("leave-team-button");

  if (!btn) return;

  btn.onclick = async () => {
    if (!confirm("Выйти из команды?")) return;

    try {
      await request("/api/team/leave/", {
        method: "POST",
        body: JSON.stringify({
          user_telegram_id: Number(state.currentTelegramId),
        }),
      });

      reload();

    } catch (err) {
      alert(err.message);
    }
  };
}