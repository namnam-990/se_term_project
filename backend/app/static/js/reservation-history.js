const reservationFilter = document.getElementById("reservation-status");
const reservationTable = document.getElementById("reservation-table");
const reservationMessage = document.getElementById("reservation-message");
const reservationEmptyLink = document.getElementById("reservation-empty-link");
const reservationRetry = document.getElementById("reservation-retry");
const reservationLabels = new Map(
  Array.from(reservationFilter.options, (option) => [option.value, option.textContent]),
);
let reservationQuery = 0;
const cancelPanel = document.getElementById("cancel-panel");
const cancelSummary = document.getElementById("cancel-summary");
const cancelReason = document.getElementById("cancel-reason");
const cancelDetail = document.getElementById("cancel-detail");
const cancelConfirm = document.getElementById("cancel-confirm");
let cancelTarget = null;

async function refreshReservations() {
  const currentQuery = ++reservationQuery;
  closeCancelPanel();
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
      // US-09: 입실 전(RESERVED)만 취소 버튼. 체크인 마감(시작+15분) 이후는 서버가 거부하고 안내 (D-26)
      const actionCell = row.insertCell();
      if (item.status === "RESERVED") {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "btn secondary small";
        button.textContent = "취소";
        button.addEventListener("click", () => openCancelPanel(item));
        actionCell.append(button);
      }
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

// ───────────── US-09 직접 취소 ─────────────
function openCancelPanel(item) {
  cancelTarget = item;
  cancelSummary.textContent =
    `${item.seat_number} 좌석 · ${item.start_at.slice(0, 16).replace("T", " ")} 예약을 취소할까요?`;
  cancelReason.value = "SCHEDULE_CHANGE";
  cancelDetail.value = "";
  cancelDetail.hidden = true;
  cancelConfirm.disabled = false;
  cancelPanel.hidden = false;
  cancelReason.focus();
}

function closeCancelPanel() {
  cancelTarget = null;
  cancelPanel.hidden = true;
}

async function confirmCancel() {
  if (!cancelTarget) return;
  cancelConfirm.disabled = true;
  try {
    await api(`/api/reservations/${cancelTarget.id}/cancel`, {
      method: "POST",
      body: {
        reason: cancelReason.value,
        detail: cancelReason.value === "OTHER" && cancelDetail.value ? cancelDetail.value : null,
      },
    });
    // 직접 취소는 노쇼 패널티 없음 (FR-X-03), 좌석은 즉시 다른 학생이 예약 가능 (FR-X-04)
    toast("예약이 취소되었습니다. 노쇼 패널티는 없습니다.", true);
    await refreshReservations();
  } catch (error) {
    toast(error.message || "취소하지 못했습니다.");
    cancelConfirm.disabled = false;
    if (error.code === "NOT_CANCELLABLE") await refreshReservations();
  }
}

cancelReason.addEventListener("change", () => {
  cancelDetail.hidden = cancelReason.value !== "OTHER";
});
cancelConfirm.addEventListener("click", confirmCancel);
document.getElementById("cancel-close").addEventListener("click", closeCancelPanel);

reservationRetry.addEventListener("click", refreshReservations);
reservationFilter.addEventListener("change", refreshReservations);
refreshReservations();
