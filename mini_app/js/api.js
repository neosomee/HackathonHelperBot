const tg = window.Telegram?.WebApp;

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
  try {
    const response = await fetch(path, {
      headers: {
        "Content-Type": "application/json",
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
        "Backend API недоступен. Откройте Mini App через http://127.0.0.1:8000/miniapp/."
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