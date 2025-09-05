// JavaScript
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("chat-form");
  const input = document.getElementById("message") || document.getElementById("chat-message");
  if (!form || !input) return;

  let composing = false;
  input.addEventListener("compositionstart", () => (composing = true));
  input.addEventListener("compositionend", () => (composing = false));

  input.addEventListener("keydown", (e) => {
    if (composing) return;
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      const value = (input.value || "").trim();
      if (!value) return;
      if (typeof form.requestSubmit === "function") form.requestSubmit();
      else form.submit();
    }
  });
});

// JavaScript
document.addEventListener("DOMContentLoaded", () => {
  const input = document.getElementById("messageInput");
  if (!input) return;
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      e.target.form?.submit();
    }
  });
});