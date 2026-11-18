const seatFilters = document.getElementById("seat-filters");
const seatGrid = document.getElementById("seat-grid");
const seatPolicy = document.getElementById("seat-policy");
const seatMessage = document.getElementById("seat-message");
const midnightHint = document.getElementById("seat-midnight-hint");
const reservePanel = document.getElementById("reserve-panel");
const reserveSummary = document.getElementById("reserve-summary");
const reserveConfirm = document.getElementById("reserve-confirm");
let selectedSeat = null; // { seat, start_at, end_at, requestKey }
const seatLabels = { AVAILABLE: "예약 가능", IN_USE: "사용 중", MINE: "내 예약", RESERVED: "예약됨" };
let seatQuery = 0;

function seatEndTimestamp(date, time) {
  if (time !== "00:00") return `${date}T${time}:00`;
  const nextDay = new Date(`${date}T00:00:00Z`);
  nextDay.setUTCDate(nextDay.getUTCDate() + 1);
  return `${nextDay.toISOString().slice(0, 10)}T00:00:00`;
}

async function refreshSeats() {
  const currentQuery = ++seatQuery;
  closeReservePanel();
  seatGrid.replaceChildren();
  seatPolicy.hidden = true;
  if (!seatFilters.checkValidity()) {
    seatMessage.textContent = "날짜와 시작·종료 시간을 모두 선택하세요.";
    return;
  }

  const values = new FormData(seatFilters);
  const date = values.get("date");
  seatMessage.textContent = "좌석 현황을 불러오는 중입니다.";
  try {
    const range = {
      start_at: `${date}T${values.get("start")}:00`,
      end_at: seatEndTimestamp(date, values.get("end")),
    };
    const { seats, policy, bookable: rangeBookable, notice } = await api("/api/seats", {
      redirectOnUnauthorized: false,
      query: range,
    });
    if (currentQuery !== seatQuery) return;
    const period = policy.exam_mode ? "당일~다음 날" : `오늘부터 ${policy.days_ahead}일 후까지`;
    seatPolicy.textContent =
      `${policy.exam_mode ? "시험 기간" : "평상시"} · 예약 가능 기간 ${period} · ` +
      `최대 예약 ${policy.max_hours}시간 · ` +
      `운영 ${String(policy.open_hour).padStart(2, "0")}:00~${String(policy.close_hour).padStart(2, "0")}:00 · ` +
      `${policy.slot_minutes}분 단위`;
    midnightHint.hidden = policy.close_hour !== 24;
    seatPolicy.hidden = false;

    const fragment = document.createDocumentFragment();
    for (const seat of seats) {
      // 구간 자체를 예약할 수 없으면(진행 중 시간대·최대 시간 초과) 좌석 클릭도 막음 (D-28)
      const bookable = rangeBookable !== false && seat.status === "AVAILABLE";
      const tile = document.createElement(bookable ? "button" : "div");
      tile.className = `seat seat-tile ${seat.status}`;
      if (bookable) {
        tile.type = "button";
        tile.setAttribute("aria-label", `${seat.seat_number} 좌석 예약`);
        tile.addEventListener("click", () => openReservePanel(seat, range));
      }
      tile.style.gridRowStart = seat.grid_row;
      tile.style.gridColumnStart = seat.grid_col;
      const number = document.createElement("strong");
      number.textContent = seat.seat_number;
      const label = document.createElement("span");
      label.textContent = seatLabels[seat.status];
      tile.append(number, label);
      fragment.append(tile);
    }
    seatGrid.append(fragment);
    const available = seats.filter((seat) => seat.status === "AVAILABLE").length;
    if (rangeBookable === false) {
      // US-04 AC3: 현황은 보여주되 이 구간은 예약할 수 없다는 이유를 안내
      seatMessage.textContent = `${notice} (현황 확인만 가능해요)`;
    } else if (!seats.length) {
      seatMessage.textContent = "조회할 수 있는 좌석이 없습니다.";
    } else if (!available) {
      seatMessage.textContent = `선택한 시간대는 만석입니다. (전체 ${seats.length}석)`;
    } else {
      seatMessage.textContent = `예약 가능 ${available}석 / 전체 ${seats.length}석`;
    }
  } catch (error) {
    if (currentQuery !== seatQuery) return;
    if (error.status === 401) {
      location.href = "/login";
      return;
    }
    const message = error.status ? error.message : "좌석 현황을 불러오지 못했습니다.";
    seatMessage.textContent = `${message} 다시 조회하려면 조회 버튼을 누르세요.`;
  }
}

// ───────────── US-05 좌석 예약 ─────────────
function openReservePanel(seat, range) {
  selectedSeat = {
    seat,
    ...range,
    // 같은 좌석·시간을 다시 누르기 전까지 같은 키 → 더블 클릭해도 예약 1건 (서버 request_key)
    requestKey: typeof newRequestKey === "function" ? newRequestKey() : `${Date.now()}-${Math.random()}`,
  };
  const fmt = (s) => s.slice(0, 16).replace("T", " ");
  reserveSummary.textContent = `${seat.seat_number} 좌석 · ${fmt(range.start_at)} ~ ${fmt(range.end_at)}`;
  reserveConfirm.disabled = false;
  reservePanel.hidden = false;
  reserveConfirm.focus();
}

function closeReservePanel() {
  selectedSeat = null;
  reservePanel.hidden = true;
}

async function confirmReservation() {
  if (!selectedSeat) return;
  reserveConfirm.disabled = true;
  try {
    const reservation = await api("/api/reservations", {
      method: "POST",
      body: {
        seat_id: selectedSeat.seat.seat_id,
        start_at: selectedSeat.start_at,
        end_at: selectedSeat.end_at,
        request_key: selectedSeat.requestKey,
      },
    });
    toast(`${reservation.seat_number} 좌석 예약이 완료되었습니다.`, true);
    await refreshSeats(); // 방금 예약한 좌석이 '내 예약'으로 바뀐 것을 바로 보여줌
  } catch (error) {
    // 서버 안내 문구를 그대로 표시 (이미 선택된 좌석, 같은 시간대 중복, 이용 제한·해제일, 최대 시간 등)
    toast(error.message || "예약하지 못했습니다.");
    reserveConfirm.disabled = false;
    if (error.code === "SEAT_ALREADY_RESERVED") await refreshSeats();
  }
}

reserveConfirm.addEventListener("click", confirmReservation);
document.getElementById("reserve-close").addEventListener("click", closeReservePanel);

const koreaDate = new Intl.DateTimeFormat("en-CA", {
  timeZone: "Asia/Seoul", year: "numeric", month: "2-digit", day: "2-digit",
}).formatToParts(new Date());
const dateParts = Object.fromEntries(koreaDate.map(({ type, value }) => [type, value]));
seatFilters.elements.namedItem("date").value = `${dateParts.year}-${dateParts.month}-${dateParts.day}`;
seatFilters.addEventListener("change", refreshSeats);
seatFilters.addEventListener("submit", (event) => {
  event.preventDefault();
  refreshSeats();
});
