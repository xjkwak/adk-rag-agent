(function () {
  var script = document.currentScript;
  var apiBase = (script && script.getAttribute("data-api-base")) || "/api";
  var theme = (script && script.getAttribute("data-theme")) || "light";
  var appPath = "/app/intake?embed=1";

  var btn = document.createElement("button");
  btn.setAttribute("aria-label", "Open Support Intake");
  btn.innerHTML = "💬";
  btn.style.cssText =
    "position:fixed;bottom:24px;right:24px;width:56px;height:56px;border-radius:50%;" +
    "border:none;background:#6366f1;color:#fff;font-size:24px;cursor:pointer;" +
    "box-shadow:0 4px 12px rgba(0,0,0,0.2);z-index:99998;";

  var panel = document.createElement("div");
  panel.style.cssText =
    "display:none;position:fixed;bottom:96px;right:24px;width:400px;max-width:calc(100vw - 48px);" +
    "height:560px;max-height:calc(100vh - 120px);border-radius:12px;overflow:hidden;" +
    "box-shadow:0 8px 32px rgba(0,0,0,0.25);z-index:99999;background:" +
    (theme === "dark" ? "#1a1a1a" : "#fff") + ";";

  var iframe = document.createElement("iframe");
  iframe.src = appPath;
  iframe.title = "Support Intake Assistant";
  iframe.style.cssText = "width:100%;height:100%;border:none;";
  panel.appendChild(iframe);

  var open = false;
  btn.addEventListener("click", function () {
    open = !open;
    panel.style.display = open ? "block" : "none";
  });

  document.body.appendChild(btn);
  document.body.appendChild(panel);
})();
