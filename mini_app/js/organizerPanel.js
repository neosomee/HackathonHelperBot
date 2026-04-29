// js/organizerPanel.js — Панель организатора Telegram Mini App
import { request } from './api.js';
import { showScreen, escapeHtml } from './utils.js';

class OrganizerPanel {
  constructor() {
    this.telegramId = null;
    this.hackathonData = null;
    this.panelContainer = document.getElementById('manage-hackathon-panel');
    this.triggerButton = document.getElementById('manage-hackathon-button');
    this.messageEl = document.getElementById('message'); // глобальное сообщение из index.html
  }

  async init() {
    // 1. Получаем telegram_id
    if (window.Telegram?.WebApp?.initDataUnsafe?.user?.id) {
      this.telegramId = window.Telegram.WebApp.initDataUnsafe.user.id;
    } else {
      console.warn('telegram_id не обнаружен');
      return;
    }

    if (!this.panelContainer || !this.triggerButton) {
      console.error('Не найдены элементы manage-hackathon-button или manage-hackathon-panel');
      return;
    }

    // 2. Проверяем права
    const isOrganizer = await this.checkPermissions();
    if (!isOrganizer) {
      this.triggerButton.style.display = 'none';
      return;
    }

    // 3. Показываем кнопку и при клике — переходим на экран панели
    this.triggerButton.style.display = 'block';
    this.triggerButton.addEventListener('click', async () => {
      showScreen('manage-hackathon-screen');
      await this.loadOrganizerHackathon();
    });
  }

  async checkPermissions() {
    try {
      const data = await request(`/api/hackathons/permissions/?telegram_id=${this.telegramId}`);
      return data.is_organizer === true;
    } catch (e) {
      console.error('Ошибка проверки прав:', e);
      return false;
    }
  }

  async loadOrganizerHackathon() {
    try {
      const hackathons = await request(`/api/hackathons/?organizer_telegram_id=${this.telegramId}`);
      if (Array.isArray(hackathons) && hackathons.length > 0) {
        this.hackathonData = hackathons[0]; // первый хакатон организатора
        this.renderPanel();
      } else {
        this.panelContainer.innerHTML = '<p>У вас пока нет хакатона. Создайте его через бота.</p>';
        this.hackathonData = null;
      }
    } catch (e) {
      console.error('Ошибка загрузки хакатона:', e);
      this.showMessage('Не удалось загрузить хакатон', 'error');
    }
  }

  renderPanel() {
  if (!this.hackathonData) return;

  const h = this.hackathonData;
  const name = escapeHtml(h.name || 'Без названия');
  const desc = escapeHtml(h.description || '—');
  const schedule = escapeHtml(h.schedule_sheet_url || '—');
  const recruitment = h.recruitment_open ? 'Открыт' : 'Закрыт';

  this.panelContainer.innerHTML = `
    <div class="organizer-panel-content org-card">
      <div class="org-card__header">
        <div>
          <div class="org-badge">Панель организатора</div>
          <h2 class="org-title">${name}</h2>
          <p class="org-muted">${desc}</p>
        </div>
        <div class="org-status">
          <span class="org-status__label">Набор участников</span>
          <span class="org-status__value ${h.recruitment_open ? 'is-open' : 'is-closed'}">${recruitment}</span>
        </div>
      </div>

      <div class="org-field">
        <div class="org-field__label">Ссылка на расписание</div>
        <div class="org-field__value">${schedule}</div>
      </div>

      <div class="org-tip">
        <div class="org-tip__title">Формат таблицы</div>
        <pre class="org-tip__code">start_datetime	title	notify_minutes_before
29.04.2026 18:50	хакатон начало	1</pre>
        <p class="org-tip__text">
          Уведомление уйдёт за указанное число минут до времени в колонке <b>start_datetime</b>.
        </p>
      </div>

      <div class="org-actions">
        <button id="edit-hackathon-btn" class="button secondary">✏️ Редактировать</button>
        <button id="delete-hackathon-btn" class="button danger">🗑 Удалить</button>
      </div>
    </div>

    <div id="edit-form" class="org-edit-form" style="display:none; margin-top:1rem;"></div>
  `;

  document.getElementById('edit-hackathon-btn').addEventListener('click', () => this.showEditForm());
  document.getElementById('delete-hackathon-btn').addEventListener('click', () => this.deleteHackathon());
}

showEditForm() {
  const formDiv = document.getElementById('edit-form');
  formDiv.style.display = 'block';

  formDiv.innerHTML = `
    <div class="org-card">
      <h3 class="org-subtitle">Редактировать хакатон</h3>

      <label class="org-label">
        <span>Название</span>
        <input type="text" id="edit-name" class="input" value="${escapeHtml(this.hackathonData.name || '')}">
      </label>

      <label class="org-label">
        <span>Описание</span>
        <textarea id="edit-description" class="input textarea">${escapeHtml(this.hackathonData.description || '')}</textarea>
      </label>

      <label class="org-label">
        <span>Ссылка на расписание</span>
        <input type="url" id="edit-schedule" class="input" value="${escapeHtml(this.hackathonData.schedule_sheet_url || '')}">
      </label>

      <div class="org-tip">
        <div class="org-tip__title">Подсказка по таблице</div>
        <p class="org-tip__text">
          Используй колонки: <b>start_datetime</b>, <b>title</b>, <b>notify_minutes_before</b>.
        </p>
      </div>

      <label class="org-label">
        <span>Набор участников</span>
        <select id="edit-recruitment" class="input">
          <option value="true" ${this.hackathonData.recruitment_open ? 'selected' : ''}>Открыт</option>
          <option value="false" ${!this.hackathonData.recruitment_open ? 'selected' : ''}>Закрыт</option>
        </select>
      </label>

      <div class="org-actions">
        <button id="save-edit-btn" class="button primary">Сохранить</button>
        <button id="cancel-edit-btn" class="button secondary">Отмена</button>
      </div>
    </div>
  `;

  document.getElementById('save-edit-btn').addEventListener('click', () => this.saveEdit());
  document.getElementById('cancel-edit-btn').addEventListener('click', () => {
    formDiv.style.display = 'none';
  });
}

  async saveEdit() {
    const updatedData = {
      name: document.getElementById('edit-name').value,
      description: document.getElementById('edit-description').value,
      schedule_sheet_url: document.getElementById('edit-schedule').value,
      recruitment_open: document.getElementById('edit-recruitment').value === 'true',
    };

    try {
      const updated = await request(`/api/hackathons/${this.hackathonData.id}/`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updatedData),
      });
      this.hackathonData = updated;
      this.renderPanel();
      document.getElementById('edit-form').style.display = 'none';
      this.showMessage('Хакатон обновлён!', 'success');
    } catch (e) {
      console.error(e);
      this.showMessage('Не удалось сохранить изменения', 'error');
    }
  }

  async deleteHackathon() {
    if (!confirm('Вы уверены, что хотите удалить хакатон? Это действие необратимо.')) return;

    try {
      await request(`/api/hackathons/${this.hackathonData.id}/`, {
        method: 'DELETE',
      });
      this.panelContainer.innerHTML = '<p>Хакатон удалён. Вы можете создать новый через бота.</p>';
      this.hackathonData = null;
      this.showMessage('Хакатон удалён', 'success');
    } catch (e) {
      console.error(e);
      this.showMessage('Не удалось удалить хакатон', 'error');
    }
  }

  // Вспомогательный метод для вывода глобального сообщения
  showMessage(text, type = 'info') {
    if (!this.messageEl) return;
    this.messageEl.textContent = text;
    this.messageEl.className = `message ${type}`;
    this.messageEl.style.display = 'block';
    setTimeout(() => {
      this.messageEl.style.display = 'none';
    }, 4000);
  }
}

// Автозапуск после загрузки DOM
document.addEventListener('DOMContentLoaded', () => {
  const panel = new OrganizerPanel();
  panel.init();
});