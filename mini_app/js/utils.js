export function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

export function showScreen(screenId, screens, clearMessage) {
  Object.values(screens).forEach((screen) => screen.classList.remove("active"));
  document.getElementById(screenId).classList.add("active");
  clearMessage();
}

export function showMessage(messageBox, text, isError = false) {
  messageBox.textContent = text;
  messageBox.classList.toggle("error", isError);
  messageBox.classList.remove("hidden");
}

export function clearMessage(messageBox) {
  messageBox.textContent = "";
  messageBox.classList.add("hidden");
  messageBox.classList.remove("error");
}

export function getMembershipInfo(membershipData, telegramId) {
  const memberships = Array.isArray(membershipData) ? membershipData : [];
  const userMemberships = memberships.filter(
    (item) => String(item.user?.telegram_id || "") === String(telegramId)
  );

  const captainMembership = userMemberships.find((item) => {
    return (
      item.status === "accepted" &&
      String(item.team?.captain?.telegram_id || "") === String(telegramId)
    );
  });

  if (captainMembership) {
    return {
      statusText: "Капитан",
      teamName: captainMembership.team?.name || "Без названия",
      isCaptain: true,
      hasAcceptedTeam: true,
      hasPendingApplication: false,
      teamId: captainMembership.team?.id || null,
    };
  }

  const acceptedMembership = userMemberships.find((item) => item.status === "accepted");
  if (acceptedMembership) {
    return {
      statusText: "В команде",
      teamName: acceptedMembership.team?.name || "Без названия",
      isCaptain: false,
      hasAcceptedTeam: true,
      hasPendingApplication: false,
      teamId: acceptedMembership.team?.id || null,
    };
  }

  const pendingMembership = userMemberships.find((item) => item.status === "pending");
  if (pendingMembership) {
    return {
      statusText: "Заявка отправлена",
      teamName: pendingMembership.team?.name || "Без названия",
      isCaptain: false,
      hasAcceptedTeam: false,
      hasPendingApplication: true,
      teamId: pendingMembership.team?.id || null,
    };
  }

  return {
    statusText: "Не участвует в команде",
    teamName: "Нет команды",
    isCaptain: false,
    hasAcceptedTeam: false,
    hasPendingApplication: false,
    teamId: null,
  };
}