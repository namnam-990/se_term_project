const authMessage = document.getElementById("auth-message");

function bindAuthForm(id, path, onSuccess) {
  const form = document.getElementById(id);
  if (!form) return;
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = form.querySelector("button[type=submit]");
    button.disabled = true;
    authMessage.textContent = "처리 중입니다.";
    try {
      const body = Object.fromEntries(new FormData(form));
      if (body.name === "") delete body.name;
      const data = await api(path, { method: "POST", body, redirectOnUnauthorized: false });
      authMessage.textContent = data.message || "로그인되었습니다.";
      onSuccess?.(data, body);
    } catch (error) {
      authMessage.textContent = error.message || "요청을 처리하지 못했습니다. 다시 시도하세요.";
      const link = document.getElementById("verify-link");
      if (link && error.code === "ACCOUNT_PENDING") link.hidden = false;
    } finally {
      button.disabled = false;
    }
  });
}

bindAuthForm("signup-form", "/api/auth/signup", (_, body) => {
  document.getElementById("signup-form").reset();
  const link = document.getElementById("verify-link");
  link.href = `/verify-email?email=${encodeURIComponent(body.email)}`;
  link.hidden = false;
});
bindAuthForm("login-form", "/api/auth/login", (data) => {
  // 관리자 화면은 Sprint 2 범위. 학생 전용 화면으로 보내지 않는다.
  location.href = data.role === "ROLE_STUDENT" ? "/seats" : "/";
});
bindAuthForm("verify-form", "/api/auth/email-verifications", () => {
  document.getElementById("verify-form").hidden = true;
});

async function verifyEmailLink() {
  const form = document.getElementById("verify-form");
  if (!form) return;
  const params = new URLSearchParams(location.search);
  if (params.get("email")) form.elements.email.value = params.get("email");
  const token = params.get("token");
  if (!token) return;
  // 인증 토큰을 주소 표시줄·이후 탐색의 referrer에 남기지 않는다.
  history.replaceState(null, "", "/verify-email");
  form.hidden = true;
  authMessage.textContent = "이메일을 인증하는 중입니다.";
  try {
    const data = await api("/api/auth/email-verifications", {
      method: "POST", body: { token }, redirectOnUnauthorized: false,
    });
    authMessage.textContent = data.message;
  } catch (error) {
    authMessage.textContent = error.message || "인증하지 못했습니다. 코드를 입력해 주세요.";
    form.hidden = false;
  }
}
verifyEmailLink();
