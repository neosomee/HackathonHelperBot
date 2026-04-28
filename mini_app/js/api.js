const tg = window.Telegram?.WebApp;

function computeApiBase() {
  const params = new URLSearchParams(window.location.search);
  const fromQuery = params.get("api_base");
  if (fromQuery) {
    const normalized = fromQuery.replace(/\/$/, "");
    try {
      localStorage.setItem("mini_app_api_base", normalized);
    } catch {
      /* ignore */
    }
    return normalized;
  }
  try {
    const stored = localStorage.getItem("mini_app_api_base");
    if (stored) {
      return stored.replace(/\/$/, "");
    }
  } catch {
    /* ignore */
  }
  if (window.location.protocol === "file:") {
    return "http://127.0.0.1:8000";
  }
  return "";
}

const API_BASE = computeApiBase();

export function getApiBase() {
  return API_BASE;
}

export function apiUrl(path) {
  const p = path.startsWith("/") ? path : `/${path}`;
  return API_BASE ? `${API_BASE}${p}` : p;
}

export function getTelegramId() {
  const fromTelegram = tg?.initDataUnsafe?.user?.id;
  if (fromTelegram) return String(fromTelegram);

  const params = new URLSearchParams(window.location.search);
  const fromQuery = params.get("telegram_id");
  if (fromQuery) {
    localStorage.setItem("mini_app_telegram_id", fromQuery);
    return fromQuery;
  }

  const fromStorage = localStorage.getItem("mini_app_telegram_id");
  if (fromStorage) return fromStorage;

  const fromPrompt = window.prompt("Введите Telegram ID для локальной разработки:");
  if (fromPrompt) {
    localStorage.setItem("mini_app_telegram_id", fromPrompt);
    return fromPrompt;
  }

  return null;
}

export async function request(path, options = {}) {
  const url = apiUrl(path);
  try {
    const response = await fetch(url, {
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
      ...options,
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(getErrorMessage(response.status, data));
    }

    return data;
  } catch (error) {
    if (error instanceof TypeError) {
      throw new Error(
        "Backend недоступен. Запустите Django (python manage.py runserver) и откройте страницу с параметром ?api_base=http://127.0.0.1:8000 при открытии index.html с диска."
      );
    }
    throw error;
  }
}

function getErrorMessage(statusCode, data) {
  if (data.error) return data.error;
  if (data.errors) return "Ошибка валидации. Проверьте данные и попробуйте снова.";
  if (statusCode === 404) return "Данные не найдены.";
  if (statusCode >= 500) return "Ошибка сервера. Попробуйте позже.";
  return "Не удалось выполнить запрос.";
}
