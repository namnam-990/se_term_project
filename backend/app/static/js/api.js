// 공통 fetch 래퍼 — 모든 화면은 이 함수로 API를 호출한다.
// 서버 오류 형식: { code, message }  (docs/api-contract.md)
async function api(path, { method = "GET", body, query } = {}) {
  const url = new URL(path, location.origin);
  if (query) Object.entries(query).forEach(([k, v]) => v != null && url.searchParams.set(k, v));
  const res = await fetch(url, {
    method,
    credentials: "same-origin", // HttpOnly 쿠키 자동 전송
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = res.status === 204 ? null : await res.json().catch(() => null);
  if (!res.ok) {
    const err = new Error(data?.message || `요청 실패 (${res.status})`);
    err.status = res.status;
    err.code = data?.code;
    err.data = data;
    if (res.status === 401) location.href = "/login";
    throw err;
  }
  return data;
}

function toast(message, ok = false) {
  const el = document.getElementById("toast");
  if (!el) return alert(message);
  el.textContent = message;
  el.className = ok ? "toast ok" : "toast";
  el.hidden = false;
  clearTimeout(el._t);
  el._t = setTimeout(() => (el.hidden = true), 4000);
}

// 예약 중복 전송 방지용 요청 키 (US-05)
const newRequestKey = () => crypto.randomUUID();
