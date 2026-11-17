const reservationFilter = document.getElementById("reservation-status");
const reservationTable = document.getElementById("reservation-table");
const reservationMessage = document.getElementById("reservation-message");
const reservationEmptyLink = document.getElementById("reservation-empty-link");
const reservationRetry = document.getElementById("reservation-retry");
const reservationLabels = new Map(
  Array.from(reservationFilter.options, (option) => [option.value, option.textContent]),
);
let reservationQuery = 0;

async function refreshReservations() {
  const currentQuery = ++reservationQuery;
  reservationTable.hidden = true;
  reservationEmptyLink.hidden = true;
  reservationRetry.hidden = true;
  reservationTable.tBodies[0].replaceChildren();
  reservationMessage.textContent = "내 예약을 불러오는 중입니다.";
  try {
    const { items, message } = await api("/api/me/reservations", {
      redirectOnUnauthorized: false,
      query: { status: reservationFilter.value || null },
    });
    if (currentQuery !== reservationQuery) return;
    for (const item of items) {
      const row = reservationTable.tBodies[0].insertRow();
      const values = [
        item.seat_number,
        item.start_at.slice(0, 16).replace("T", " "),
        item.end_at.slice(0, 16).replace("T", " "),
        reservationLabels.get(item.status) || item.status,
      ];
      for (const value of values) row.insertCell().textContent = value;
    }
    reservationMessage.textContent = items.length ? `예약 ${items.length}건` : message;
    reservationTable.hidden = items.length === 0;
    reservationEmptyLink.hidden = items.length !== 0;
  } catch (error) {
    if (currentQuery !== reservationQuery) return;
    if (error.status === 401) {
      location.href = "/login";
      return;
    }
    reservationMessage.textContent = error.status ? error.message : "내 예약을 불러오지 못했습니다.";
    reservationRetry.hidden = false;
  }
}

reservationRetry.addEventListener("click", refreshReservations);
reservationFilter.addEventListener("change", refreshReservations);
refreshReservations();
