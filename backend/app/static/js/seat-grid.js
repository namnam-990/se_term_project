const seatFilters = document.getElementById("seat-filters");
const seatGrid = document.getElementById("seat-grid");
const seatPolicy = document.getElementById("seat-policy");
const seatMessage = document.getElementById("seat-message");
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
    const { seats, policy } = await api("/api/seats", {
      redirectOnUnauthorized: false,
      query: {
        start_at: `${date}T${values.get("start")}:00`,
        end_at: seatEndTimestamp(date, values.get("end")),
      },
    });
    if (currentQuery !== seatQuery) return;
    seatPolicy.textContent = `${policy.exam_mode ? "시험 기간" : "평상시"} · 최대 예약 ${policy.max_hours}시간 · ${policy.slot_minutes}분 단위`;
    seatPolicy.hidden = false;

    const fragment = document.createDocumentFragment();
    for (const seat of seats) {
      const tile = document.createElement("div");
      tile.className = `seat seat-tile ${seat.status}`;
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
    if (!seats.length) {
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
