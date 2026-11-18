const seatFilters = document.getElementById("seat-filters");
const seatGrid = document.getElementById("seat-grid");
const seatPolicy = document.getElementById("seat-policy");
const seatMessage = document.getElementById("seat-message");
const startHour = seatFilters.elements.namedItem("start_hour");
const startMinute = seatFilters.elements.namedItem("start_minute");
const endHour = seatFilters.elements.namedItem("end_hour");
const endMinute = seatFilters.elements.namedItem("end_minute");
const dateInput = seatFilters.elements.namedItem("date");
let timePolicy = null; // { open_hour, close_hour, slot_minutes, max_hours }
const reservePanel = document.getElementById("reserve-panel");
const reserveSummary = document.getElementById("reserve-summary");
const reserveConfirm = document.getElementById("reserve-confirm");
let selectedSeat = null; // { seat, start_at, end_at, requestKey }
const seatLabels = { AVAILABLE: "예약 가능", IN_USE: "사용 중", MINE: "내 예약", RESERVED: "예약됨" };
let seatQuery = 0;

function seatEndTimestamp(date, time) {
  // 자정 종료(close_hour=24)는 옵션 값 "24:00" → 다음 날 00:00
  if (time !== "24:00" && time !== "00:00") return `${date}T${time}:00`;
  const nextDay = new Date(`${date}T00:00:00Z`);
  nextDay.setUTCDate(nextDay.getUTCDate() + 1);
  return `${nextDay.toISOString().slice(0, 10)}T00:00:00`;
}

async function refreshSeats() {
  const currentQuery = ++seatQuery;
  closeReservePanel();
  seatMessage.classList.remove("warn");
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
      start_at: `${date}T${toLabel(selectedStart())}:00`,
      end_at: seatEndTimestamp(date, toLabel(selectedEnd())),
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
      seatMessage.classList.add("warn");
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
    seatMessage.classList.add("warn");
    if (error.code === "OUT_OF_BOOKING_WINDOW" || error.code === "INVALID_TIME_RANGE") {
      // 지난 시간·예약 가능 기간 밖 등: 서버 안내 그대로 + 다른 시간 선택 유도
      seatMessage.textContent = `${error.message} 다른 날짜나 시간을 선택해 주세요.`;
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

// ───────────── 시간 선택: [시]·[분] 따로 고르는 드롭다운 (정책 기반, D-11: 06:00~23:00 · 30분) ─────────────
const pad = (n) => String(n).padStart(2, "0");
const toLabel = (minutes) => `${pad(Math.floor(minutes / 60))}:${pad(minutes % 60)}`;

function koreaNow() {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Seoul", year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", hourCycle: "h23",
  }).formatToParts(new Date());
  const v = Object.fromEntries(parts.map(({ type, value }) => [type, value]));
  return { date: `${v.year}-${v.month}-${v.day}`, minutes: Number(v.hour) * 60 + Number(v.minute) };
}

function addDays(date, days) {
  const d = new Date(`${date}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

// 운영 시작~종료를 단위(분)마다 나눈 경계 시각들 (자정 기준 분)
function slotBoundaries() {
  const { open_hour, close_hour, slot_minutes } = timePolicy;
  const list = [];
  for (let m = open_hour * 60; m <= close_hour * 60; m += slot_minutes) list.push(m);
  return list;
}

// 오늘 이미 끝난 칸인지 (기본값을 고를 때만 사용 — 선택 자체는 막지 않음)
function isPastStart(m) {
  const now = koreaNow();
  return dateInput.value === now.date && m + timePolicy.slot_minutes <= now.minutes;
}

const startCandidates = () => slotBoundaries().slice(0, -1); // 운영 종료 시각에는 시작 불가
const endCandidates = () => slotBoundaries().filter((m) => m > selectedStart());
const selectedStart = () => Number(startHour.value) * 60 + Number(startMinute.value);
const selectedEnd = () => Number(endHour.value) * 60 + Number(endMinute.value);

// candidates(분 목록)를 [시]·[분] 두 드롭다운으로 나눠 채움. target: 고르고 싶은 시각(분)
function fillPair(hourSelect, minuteSelect, candidates, target, isDisabled = () => false) {
  const hours = [...new Set(candidates.map((m) => Math.floor(m / 60)))];
  const usable = candidates.filter((m) => !isDisabled(m));
  const pick = usable.includes(target) ? target : usable[0] ?? candidates[0];
  hourSelect.replaceChildren(
    ...hours.map((h) => {
      const option = new Option(h === 24 ? "24 (자정)" : pad(h), String(h));
      // 그 시의 모든 분이 고를 수 없으면 시 자체를 비활성
      option.disabled = candidates.filter((m) => Math.floor(m / 60) === h).every(isDisabled);
      return option;
    }),
  );
  hourSelect.value = String(Math.floor(pick / 60));
  fillMinutes(hourSelect, minuteSelect, candidates, pick % 60, isDisabled);
}

function fillMinutes(hourSelect, minuteSelect, candidates, targetMinute, isDisabled = () => false) {
  const hour = Number(hourSelect.value);
  const inHour = candidates.filter((m) => Math.floor(m / 60) === hour);
  minuteSelect.replaceChildren(
    ...inHour.map((m) => {
      const option = new Option(pad(m % 60), String(m % 60));
      option.disabled = isDisabled(m);
      return option;
    }),
  );
  const usable = inHour.filter((m) => !isDisabled(m)).map((m) => m % 60);
  minuteSelect.value = String(usable.includes(targetMinute) ? targetMinute : usable[0] ?? 0);
}

function rebuildEnd(preferredEnd) {
  const start = selectedStart();
  const ends = endCandidates();
  // 기본 종료: 시작 + 2시간 (최대 이용 시간·운영 종료를 넘지 않게)
  const fallback = Math.min(start + Math.min(120, timePolicy.max_hours * 60), ends.at(-1));
  fillPair(endHour, endMinute, ends, preferredEnd != null && preferredEnd > start ? preferredEnd : fallback);
}

function rebuildStart() {
  const starts = startCandidates();
  const keep = startHour.value !== "" ? selectedStart() : null;
  // 기본값은 '아직 시작 전'인 첫 칸 (진행 중인 칸은 고를 수는 있지만 예약은 안 되므로 기본값에서 제외)
  const now = koreaNow();
  const isToday = dateInput.value === now.date;
  const firstOpen =
    starts.find((m) => !isToday || m >= now.minutes) ?? starts.find((m) => !isPastStart(m));
  const target = keep != null && !isPastStart(keep) && starts.includes(keep) ? keep : firstOpen;
  const previousEnd = endHour.value !== "" ? selectedEnd() : null;
  // 지난 시간도 고를 수 있게 둔다 → 서버가 '이미 끝난 시간대' / '예약 불가' 이유를 안내 (US-04 AC3)
  fillPair(startHour, startMinute, starts, target);
  rebuildEnd(previousEnd);
}

async function initTimeSelects() {
  try {
    timePolicy = await api("/api/policies/current", { redirectOnUnauthorized: false });
  } catch (error) {
    if (error.status === 401) {
      location.href = "/login";
      return;
    }
    seatMessage.textContent = error.message || "운영 정책을 불러오지 못했습니다.";
    return;
  }
  const now = koreaNow();
  // 오늘 마지막 칸까지 끝났으면(운영 종료 이후) 내일로
  const lastStart = timePolicy.close_hour * 60 - timePolicy.slot_minutes;
  dateInput.value = lastStart + timePolicy.slot_minutes <= now.minutes ? addDays(now.date, 1) : now.date;
  rebuildStart();
  refreshSeats();
}

dateInput.addEventListener("change", () => {
  if (timePolicy) rebuildStart();
  refreshSeats();
});
startHour.addEventListener("change", () => {
  const previousEnd = selectedEnd();
  fillMinutes(startHour, startMinute, startCandidates(), Number(startMinute.value));
  rebuildEnd(previousEnd);
  refreshSeats();
});
startMinute.addEventListener("change", () => {
  rebuildEnd(selectedEnd());
  refreshSeats();
});
endHour.addEventListener("change", () => {
  fillMinutes(endHour, endMinute, endCandidates(), Number(endMinute.value));
  refreshSeats();
});
endMinute.addEventListener("change", refreshSeats);
seatFilters.addEventListener("submit", (event) => {
  event.preventDefault();
  refreshSeats();
});
initTimeSelects();
