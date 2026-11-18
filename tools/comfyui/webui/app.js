"use strict";

/* ============================================================
   漫转写实 · 网页控制台
   ============================================================ */

const $ = (id) => document.getElementById(id);

const state = {
  config: null,
  settings: null,
  viewer: { root: "", job: "", manual: false, detected: "" },
  jobs: [],
  pairState: null,
  pairs: null,
  pairsJob: null,
  pairsAt: 0,
  viewing: null,
  lastPairKey: "",
  follow: true,
  phase: "idle",
  prevPhase: "idle",
  lastStatus: null,
  logSeq: 0,
  serverEpoch: null,
  semiToken: null,
  suppressSemiToken: null,
  semiPrevFocus: null,
  dirTarget: null,
  modalPath: "",
  dirOpen: false,
  saveTimer: null,
  folderTimer: null,
  pollBusy: false,
  failures: 0,
  connected: true,
  logCollapsed: false,
  immersive: false,
  sidebarOpen: false,
  drawerOpen: false,
  startPending: false,
  navLast: 0,
};

const PHASE_LABEL = {
  idle: "空闲",
  running: "处理中",
  paused: "已暂停",
  waiting: "等待确认",
  stopping: "正在停止",
};

const ACTIVE_PHASES = new Set(["running", "paused", "waiting", "stopping"]);

/* ---------------- 基础工具 ---------------- */

function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

function fmtClock(d = new Date()) {
  const p = (x) => String(x).padStart(2, "0");
  return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}

function fmtTime(ts, withDate = false) {
  if (!ts) return "—";
  const d = new Date(Number(ts) * 1000);
  if (Number.isNaN(d.getTime())) return "—";
  const p = (x) => String(x).padStart(2, "0");
  const now = new Date();
  const sameDay = d.toDateString() === now.toDateString();
  const hm = `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
  if (!withDate && sameDay) return hm;
  return `${p(d.getMonth() + 1)}-${p(d.getDate())} ${hm}`;
}

function fmtDur(ms) {
  if (!Number.isFinite(ms) || ms < 0) return "";
  const s = Math.floor(ms / 1000);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  const r = s % 60;
  if (m < 60) return `${m}:${String(r).padStart(2, "0")}`;
  const h = Math.floor(m / 60);
  return `${h}:${String(m % 60).padStart(2, "0")}:${String(r).padStart(2, "0")}`;
}

function imgURL(job, side, name, mtime) {
  return "/api/image?job=" + encodeURIComponent(job || "")
    + "&side=" + encodeURIComponent(side)
    + "&name=" + encodeURIComponent(name || "")
    + "&t=" + Math.round(Number(mtime) || 0);
}

function inputImgURL(name, mtime) {
  return "/api/input-image?name=" + encodeURIComponent(name || "")
    + "&t=" + Math.round(Number(mtime) || 0);
}

async function getJSON(url, timeout = 12000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);
  try {
    const r = await fetch(url, { cache: "no-store", signal: controller.signal });
    if (!r.ok) throw new Error("HTTP " + r.status);
    return await r.json();
  } finally {
    clearTimeout(timer);
  }
}

async function postJSON(url, data, timeout = 20000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);
  try {
    const r = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data || {}),
      cache: "no-store",
      signal: controller.signal,
    });
    if (!r.ok) throw new Error("HTTP " + r.status);
    return await r.json();
  } finally {
    clearTimeout(timer);
  }
}

function toast(text, kind = "info", ms = 4200) {
  const box = $("toasts");
  while (box.children.length >= 4) box.removeChild(box.firstChild);
  const el = document.createElement("div");
  el.className = `toast ${kind}`;
  el.textContent = text;
  box.appendChild(el);
  requestAnimationFrame(() => el.classList.add("show"));
  setTimeout(() => {
    el.classList.remove("show");
    setTimeout(() => el.remove(), 260);
  }, ms);
}

function setSaveState(text, isError = false) {
  const el = $("save-state");
  el.textContent = text;
  el.classList.toggle("error", isError);
}

function isEditable(el) {
  if (!el) return false;
  const tag = el.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT"
    || el.isContentEditable;
}

/* ---------------- 启动 ---------------- */

async function boot() {
  bindEvents();
  syncSidebarInert();
  setDrawerInert(true);
  initLogEmpty();
  pollComfy();
  setInterval(pollComfy, 15000);
  setInterval(tickElapsed, 500);
  setInterval(autoFollowOutput, 12000);
  pollStatus();
  pollPairs();

  try {
    const cfg = await getJSON("/api/config");
    applyConfig(cfg);
    toast("参数已加载，可以开始处理", "ok", 2600);
  } catch (e) {
    setNet(false);
    toast("无法读取配置，请确认服务端仍在运行", "err", 8000);
    setTimeout(async () => {
      try {
        const cfg = await getJSON("/api/config");
        applyConfig(cfg);
        setNet(true);
      } catch (_) { /* 保持重试由状态轮询负责 */ }
    }, 4000);
  }
}

function applyConfig(cfg) {
  state.config = cfg;
  state.viewer = cfg.viewer || { root: "", job: "", manual: false, detected: "" };
  state.serverEpoch = cfg.server_epoch;

  // 处理模式
  const modeSel = $("mode");
  modeSel.innerHTML = "";
  for (const m of cfg.modes || []) {
    const o = document.createElement("option");
    o.value = m;
    o.textContent = m;
    modeSel.appendChild(o);
  }

  // 工作流
  const wfSel = $("workflow");
  wfSel.innerHTML = "";
  for (const wf of cfg.workflows || []) {
    const o = document.createElement("option");
    o.value = wf.name;
    o.textContent = wf.name;
    wfSel.appendChild(o);
  }

  applySettingsToUI(cfg.settings);
  state.settings = { ...cfg.settings };
  applyWorkflowUI({ preferSaved: true });
  renderPresets("main");
  if (state.semiToken) renderPresets("semi");

  updateBrowseUI();
  loadJobs(state.viewer.job || "", { quiet: true });
  refreshInputCount();
  initLogEmpty();
  setSaveState(`已载入上次参数 · ${fmtClock(new Date())}`);
  if (cfg.settings && cfg.settings.start_index > 0 && cfg.settings.resume_file) {
    toast(`已恢复断点：索引 ${cfg.settings.start_index}`, "info", 4000);
  }
}

function applySettingsToUI(s) {
  if (!s) return;
  $("in-folder").value = s.input_folder || "";
  $("out-folder").value = s.output_folder || "";
  $("prompt").value = s.prompt || "";
  setSelectValue($("mode"), s.process_mode);
  setSelectValue($("workflow"), s.workflow);
  $("strength").value = s.strength_model != null ? s.strength_model : 1.0;
  $("steps").value = s.steps != null ? s.steps : 9;
  $("cfg").value = s.cfg != null ? s.cfg : 1.4;
  $("resize").value = s.resize_longest_edge != null ? s.resize_longest_edge : 1440;
  $("start-index").value = s.start_index != null ? s.start_index : 0;
  $("rail-mode-label").textContent = s.process_mode || "全自动模式";
}

function setSelectValue(sel, value) {
  if (value == null) return;
  if (![...sel.options].some((o) => o.value === value)) {
    const o = document.createElement("option");
    o.value = value;
    o.textContent = value;
    sel.appendChild(o);
  }
  sel.value = value;
}

function applyWorkflowUI({ preferSaved = false } = {}) {
  if (!state.config) return;
  const wf = currentWorkflow();
  $("row-lora").classList.toggle("hidden", !wf || !wf.has_lora);
  $("row-strength").classList.toggle("hidden", !wf || !wf.has_lora);
  $("row-steps").classList.toggle("hidden", !wf || !wf.has_steps);
  $("row-cfg").classList.toggle("hidden", !wf || !wf.has_cfg);
  $("row-checkpoint").classList.toggle("hidden", !wf || !wf.has_checkpoint);
  if (wf) {
    $("steps-hint").textContent = wf.steps_node
      ? `整数 · 节点 ${wf.steps_node}` : "";
    $("cfg-hint").textContent = wf.cfg_node
      ? `0–30 · 节点 ${wf.cfg_node}` : "";
  }

  let changed = false;
  if (wf && wf.has_lora) {
    const files = state.config.loras[wf.name] || [];
    const warning = state.config.lora_warnings[wf.name] || "";
    const saved = preferSaved
      ? (state.settings && state.settings.lora) || $("lora").value || ""
      : $("lora").value;
    const picked = chooseModel(files, saved, wf.lora_default || "", warning);
    changed = fillSelect($("lora"), files, picked, warning);
    $("lora-warning").textContent = warning
      || (files.length ? "" : "未找到 LoRA 模型，请检查模型目录");
    $("lora-warning").classList.toggle("hidden", !$("lora-warning").textContent);
  } else {
    $("lora-warning").textContent = "";
  }

  if (wf && wf.has_checkpoint) {
    const files = state.config.checkpoints || [];
    const warning = state.config.checkpoint_warning || "";
    const saved = preferSaved
      ? (state.settings && state.settings.checkpoint) || $("checkpoint").value || ""
      : $("checkpoint").value;
    const fallback = state.config.checkpoint_default || "";
    const picked = chooseModel(files, saved, fallback, warning);
    changed = fillSelect($("checkpoint"), files, picked, warning) || changed;
    $("checkpoint-warning").textContent = warning
      || (files.length ? "" : "未找到 Checkpoint 模型");
    $("checkpoint-warning").classList.toggle("hidden", !$("checkpoint-warning").textContent);
  } else {
    $("checkpoint-warning").textContent = "";
  }
  return changed;
}

function currentWorkflow() {
  if (!state.config) return null;
  const name = $("workflow").value;
  return (state.config.workflows || []).find((w) => w.name === name) || null;
}

function chooseModel(files, saved, fallback, warning) {
  if (saved && files.includes(saved)) return saved;
  if (warning && saved) return saved; // 模型目录暂时不可用时保留已保存的选择
  if (fallback && files.includes(fallback)) return fallback;
  return files[0] || saved || "";
}

/** 填充下拉框，返回选中值是否发生变化 */
function fillSelect(sel, items, picked, warning) {
  const before = sel.value;
  const values = Array.isArray(items) ? [...items] : [];
  let target = picked || "";
  if (target && !values.includes(target)) values.unshift(target);
  if (!values.length) {
    sel.innerHTML = "";
    const o = document.createElement("option");
    o.value = "";
    o.textContent = warning ? "（模型目录不可用）" : "（无可用模型）";
    sel.appendChild(o);
    sel.value = "";
    return before !== "";
  }
  sel.innerHTML = "";
  for (const v of values) {
    const o = document.createElement("option");
    o.value = v;
    o.textContent = v;
    sel.appendChild(o);
  }
  if (!values.includes(target)) target = values[0];
  sel.value = target;
  return before !== sel.value;
}

/* ---------------- 参数收集与保存 ---------------- */

function collectSettings() {
  return {
    input_folder: $("in-folder").value.trim(),
    output_folder: $("out-folder").value.trim(),
    prompt: $("prompt").value,
    workflow: $("workflow").value,
    lora: $("lora").value || "",
    checkpoint: $("checkpoint").value || "",
    strength_model: clampNumber(parseFloat($("strength").value), 0.1, 10, 1.0),
    steps: Math.round(clampNumber(parseFloat($("steps").value), 1, 200, 9)),
    cfg: clampNumber(parseFloat($("cfg").value), 0, 30, 1.4),
    resize_longest_edge: Math.round(clampNumber(parseFloat($("resize").value), 256, 8192, 1440)),
    process_mode: $("mode").value || "全自动模式",
    start_index: Math.max(0, Math.floor(clampNumber(parseFloat($("start-index").value), 0, 999999, 0))),
  };
}

function clampNumber(v, min, max, fallback) {
  if (!Number.isFinite(v)) return fallback;
  return Math.min(max, Math.max(min, v));
}

function saveSoon() {
  clearTimeout(state.saveTimer);
  state.saveTimer = setTimeout(saveSettings, 500);
}

async function saveSettings() {
  state.saveTimer = null;
  if (!state.config) return;
  const s = collectSettings();
  state.settings = { ...(state.settings || {}), ...s };
  setSaveState("保存中…");
  try {
    const d = await postJSON("/api/batch-settings", s);
    if (!d.ok) {
      setSaveState("保存失败", true);
      toast(d.error || "保存参数失败", "err");
      return;
    }
    mergeServerMeta(d.settings);
    setSaveState(`已保存 ${fmtClock(new Date())}`);
  } catch (e) {
    setSaveState("保存失败（连接中断）", true);
  }
}

function mergeServerMeta(settings) {
  if (!settings || !state.settings) return;
  state.settings.input_count = settings.input_count;
  state.settings.start_max = settings.start_max;
  state.settings.resume_file = settings.resume_file;
  state.settings.updated = settings.updated;
  updateFolderHints();
}

function updateFolderHints() {
  const s = state.settings || {};
  const count = s.input_count;
  const folder = $("in-folder").value.trim();
  const hint = $("in-count");
  if (!folder) {
    hint.textContent = "—";
    hint.classList.remove("warn");
  } else if (count == null) {
    hint.textContent = "正在统计图片…";
    hint.classList.remove("warn");
  } else if (count < 0) {
    hint.textContent = "目录不存在或无法读取";
    hint.classList.add("warn");
  } else if (count === 0) {
    hint.textContent = "目录中没有支持的图片（.jpg/.jpeg/.png/.webp）";
    hint.classList.add("warn");
  } else {
    hint.textContent = `共 ${count} 张图片 · 索引 0–${count - 1}`;
    hint.classList.remove("warn");
  }

  const startEl = $("start-hint");
  if (count > 0) {
    const idx = Number($("start-index").value) || 0;
    const valid = idx >= 0 && idx < count;
    const resume = (valid && idx > 0 && s.resume_file)
      ? ` · 断点 ${s.resume_file}` : "";
    startEl.textContent = `${valid ? `将处理第 ${idx + 1} 张` : "索引超出范围"}${resume}`;
    startEl.classList.toggle("warn", !valid);
  } else {
    startEl.textContent = "0 = 从第一张开始";
    startEl.classList.remove("warn");
  }
  $("start-index").max = count > 0 ? String(count - 1) : "";
}

async function refreshInputCount() {
  const folder = $("in-folder").value.trim();
  if (!folder) {

    if (state.settings) {
      state.settings.input_count = 0;
      state.settings.start_max = 0;
      state.settings.resume_file = "";
    }
    updateFolderHints();
    return;
  }
  try {
    const d = await getJSON("/api/input-list?folder=" + encodeURIComponent(folder), 8000);
    if ($("in-folder").value.trim() !== folder) return; // 用户已换成另一个目录
    if (!state.settings) state.settings = {};
    if (d.ok) {
      state.settings.input_count = d.count;
      state.settings.start_max = Math.max(0, d.count - 1);
    } else {
      state.settings.input_count = -1;
    }
    updateFolderHints();
  } catch (e) {
    /* 保持原提示，等保存响应再更新 */
  }
}

/* ---------------- 运行控制 ---------------- */

async function startRun() {
  if (state.startPending) return;
  if (state.phase !== "idle") return;
  const s = collectSettings();
  if (!s.input_folder) return toast("请先选择输入文件夹", "err");
  if (!s.output_folder) return toast("请先选择输出文件夹", "err");

  state.startPending = true;
  $("btn-start").disabled = true;
  $("btn-start").textContent = "正在启动…";
  try {
    const d = await postJSON("/api/run/start", { settings: s });
    if (!d.ok) {
      toast(d.error || "启动失败", "err", 6500);
      return;
    }
    state.follow = true;
    $("chk-follow").checked = true;
    state.lastPairKey = "";
    state.semiToken = null;
    toast("已开始处理", "ok");
    if (!state.viewer.manual && s.output_folder) {
      setViewerRoot(s.output_folder, s.output_folder, false);
      persistViewer();
      loadJobs(s.output_folder, { quiet: true });
    }
    await syncAfterRunStart();
    pollComfy();
    pollStatusNow();
  } catch (e) {
    toast("启动请求失败，请检查服务端连接", "err", 6000);
  } finally {
    state.startPending = false;
    if (!state.lastStatus || state.lastStatus.phase === "idle") {
      $("btn-start").disabled = false;
      $("btn-start").textContent = "▶ 开始处理";
    }
  }
}

async function syncAfterRunStart() {
  try {
    const d = await getJSON("/api/batch-settings", 6000);
    if (d.ok && state.settings) {
      state.settings.start_index = d.settings.start_index;
      mergeServerMeta(d.settings);
    }
  } catch (e) { /* ignore */ }
}

async function pauseRun() {
  try {
    const d = await postJSON("/api/run/pause", {});
    if (!d.ok) return toast(d.error || "暂停失败", "err");
  } catch (e) {
    toast("暂停请求失败", "err");
  }
  pollStatusNow();
}

async function resumeRun() {
  try {
    const d = await postJSON("/api/run/resume", {});
    if (!d.ok) return toast(d.error || "继续失败", "err");
  } catch (e) {
    toast("继续请求失败", "err");
  }
  pollStatusNow();
}

async function stopRun() {
  if (!window.confirm("确定停止处理吗？\n当前图片会中断，断点会保留，下次可从同一张继续。")) {
    return;
  }
  try {
    const d = await postJSON("/api/run/stop", {});
    if (!d.ok) return toast(d.error || "停止失败", "err");
    toast("正在停止，请稍候…", "warn");
  } catch (e) {
    toast("停止请求失败", "err");
  }
  pollStatusNow();
}

/* ---------------- 状态轮询 ---------------- */

function pollStatusNow() {
  setTimeout(pollStatus, 0);
}

async function pollStatus() {
  if (state.pollBusy) {
    setTimeout(pollStatus, 700);
    return;
  }
  state.pollBusy = true;
  let delay = 1000;
  try {
    let d = await getJSON(`/api/status?since=${state.logSeq}`, 12000);
    if (state.serverEpoch != null && d.server_epoch !== state.serverEpoch) {
      // 服务端重启：日志序号和运行状态都从零开始
      state.serverEpoch = d.server_epoch;
      state.logSeq = 0;
      clearLogDisplay();
      d = await getJSON("/api/status?since=0", 12000);
    } else if (state.serverEpoch == null) {
      state.serverEpoch = d.server_epoch;
    }
    state.failures = 0;
    setNet(true);
    handleStatus(d);
  } catch (e) {
    state.failures += 1;
    setNet(false);
    delay = 2000;
    if (state.failures === 2) {
      toast("与服务器断开连接，正在自动重试…", "err", 6000);
    }
  } finally {
    state.pollBusy = false;
    setTimeout(pollStatus, document.hidden ? 2600 : delay);
  }
}

function handleStatus(d) {
  const prev = state.prevPhase;
  state.lastStatus = d;
  state.phase = d.phase;
  state.prevPhase = d.phase;

  appendLogs(d.logs || []);
  state.logSeq = Number(d.last_seq) || state.logSeq;

  updatePhaseUI(d);
  updateRunCard(d);
  updateDock(d);
  syncControls(d);

  // 运行结束的瞬间：同步断点参数 + 刷新预览
  if (ACTIVE_PHASES.has(prev) && d.phase === "idle") {
    onRunFinished(d);
  }

  if (d.waiting_semi && d.semi) {
    if (state.semiToken === d.semi.token) {
      // 已经打开，保留用户正在编辑的提示词
    } else if (state.suppressSemiToken === d.semi.token) {
      // 本次决定已提交，等后台把 waiting_semi 清掉，避免弹窗重开
    } else {
      openSemi(d);
    }
  } else if (!d.waiting_semi) {
    state.suppressSemiToken = null;
    if (state.semiToken) closeSemi();
  }
}

async function onRunFinished(d) {
  try {
    const r = await getJSON("/api/batch-settings", 6000);
    if (r.ok) {
      if (document.activeElement !== $("start-index")) {
        $("start-index").value = r.settings.start_index;
      }
      mergeServerMeta(r.settings);
      if (state.settings) state.settings.start_index = r.settings.start_index;
      updateFolderHints();
    }
  } catch (e) { /* ignore */ }

  if (d.completed) {
    toast(`处理完成：${d.last_summary || ""}`, "ok", 7000);
  } else if (d.total > 0) {
    toast(`已停止：${d.last_summary || ""}`, "warn", 7000);
  }
  setSaveState(`已更新 ${fmtClock(new Date())}`);

  // 有失败时自动展开日志，方便直接看到原因
  if ((Number(d.fail) || 0) > 0 && state.logCollapsed) {
    state.logCollapsed = false;
    const box = $("log-box");
    box.classList.remove("collapsed");
    $("btn-log-toggle").textContent = "收起";
    requestAnimationFrame(() => { box.scrollTop = box.scrollHeight; });
  }
  if (state.follow) {
    state.lastPairKey = "";
    refreshPairState(true);
    ensurePairs(true);
  }
}

function updatePhaseUI(d) {
  const phase = d.phase || "idle";
  const pill = $("phase-pill");
  pill.className = `phase-pill ${phase}`;
  $("phase-text").textContent = PHASE_LABEL[phase] || "空闲";
  document.body.dataset.phase = phase;
  const cmp = $("compare");
  cmp.classList.toggle("running", phase === "running");
  cmp.classList.toggle("waiting", phase === "waiting");
  cmp.classList.toggle("stopping", phase === "stopping");
}

function updateRunCard(d) {
  const phase = d.phase || "idle";
  const total = Number(d.total) || 0;
  const index = Number(d.index) || 0;

  $("rail-phase-text").textContent = PHASE_LABEL[phase] || "空闲";
  $("rail-phase-text").className = phase;

  $("run-stats").textContent = total
    ? `成功 ${d.success} · 失败 ${d.fail}`
    : "—";

  const bar = $("rail-progress");
  if (phase === "waiting" || phase === "paused") bar.className = "progress " + phase;
  else if (phase === "stopping") bar.className = "progress stopping";
  else if (phase === "running") bar.className = "progress running";
  else if (phase === "idle" && d.completed) {
    bar.className = (Number(d.fail) || 0) > 0
      ? "progress warn-done"
      : "progress completed";
  } else bar.className = "progress";

  const pct = total ? Math.min(100, Math.max(0, Number(d.progress) || 0)) : 0;
  $("rail-progress-fill").style.width = pct + "%";

  let text = "准备就绪";
  if (total) {
    if (phase === "running") {
      text = `${Math.min(index + 1, total)}/${total} · ${d.current_file || ""}`;
    } else if (phase === "waiting") {
      text = `等待确认 · ${Math.min(index + 1, total)}/${total}`;
    } else if (phase === "paused") {
      text = `已暂停 · ${Math.min(index + 1, total)}/${total}`;
    } else if (phase === "stopping") {
      text = "正在停止…";
    } else {
      text = d.last_summary || (d.completed ? "全部完成" : "准备就绪");
    }
  }
  $("rail-progress-text").textContent = text;
  $("rail-progress-text").title = text;
  updateElapsed(d);

  const startBtn = $("btn-start");
  if (state.startPending) {
    startBtn.textContent = "正在启动…";
  } else if (phase === "idle") {
    startBtn.textContent = "▶ 开始处理";
  } else if (phase === "waiting") {
    startBtn.textContent = "等待确认…";
  } else if (phase === "stopping") {
    startBtn.textContent = "正在停止…";
  } else {
    startBtn.textContent = "● 处理中";
  }
}

function updateElapsed(d = state.lastStatus) {
  const el = $("rail-elapsed");
  if (!d || !d.running) {
    el.textContent = "";
    return;
  }
  const now = Date.now() / 1000;
  const parts = [];
  if (d.current_started) parts.push(`本张 ${fmtDur((now - d.current_started) * 1000)}`);
  if (d.started_at) parts.push(`总计 ${fmtDur((now - d.started_at) * 1000)}`);
  el.textContent = parts.join(" · ");
}

function tickElapsed() {
  updateElapsed(state.lastStatus);
}

function updateDock(d) {
  const phase = d.phase || "idle";
  $("dock-phase-text").textContent = PHASE_LABEL[phase] || "空闲";
  const total = Number(d.total) || 0;
  let text = "准备就绪";
  if (total) {
    if (phase === "idle") text = d.last_summary || (d.completed ? "全部完成" : "准备就绪");
    else if (phase === "waiting") text = `待确认 · ${Math.min(d.index + 1, total)}/${total}`;
    else if (phase === "paused") text = `已暂停 · ${Math.min(d.index + 1, total)}/${total}`;
    else if (phase === "stopping") text = "正在停止…";
    else text = `${Math.min(d.index + 1, total)}/${total} · ${d.current_file || ""}`;
  }
  $("dock-stats").textContent = text;
  const pct = total ? Math.min(100, Math.max(0, Number(d.progress) || 0)) : 0;
  $("dock-fill").style.width = pct + "%";

  const btn = $("dock-action");
  if (phase === "running") { btn.textContent = "暂停"; btn.disabled = false; }
  else if (phase === "paused") { btn.textContent = "继续"; btn.disabled = false; }
  else if (phase === "waiting") { btn.textContent = "待确认"; btn.disabled = true; }
  else if (phase === "stopping") { btn.textContent = "停止中"; btn.disabled = true; }
  else { btn.textContent = "开始"; btn.disabled = false; }
}

function syncControls(d) {
  const locked = d.running;
  for (const id of ["in-folder", "out-folder", "mode", "workflow", "start-index"]) {
    $(id).disabled = locked;
  }
  document.querySelectorAll('[data-browse="input"],[data-browse="output"]').forEach((b) => {
    b.disabled = locked;
  });
  $("btn-reload").disabled = locked;
  $("btn-start").disabled = locked || state.startPending;
  $("btn-pause").disabled = !locked || d.paused || d.waiting_semi || d.stopping;
  $("btn-resume").disabled = !locked || !d.paused || d.stopping;
  $("btn-stop").disabled = !locked || d.stopping;
  $("rail-mode-label").textContent = $("mode").value || "全自动模式";
}

function setNet(ok) {
  if (state.connected === ok && $("net-banner").classList.contains("hidden") === ok) return;
  state.connected = ok;
  $("server-dot").className = "dot " + (ok ? "online" : "offline");
  $("server-pill").className = "server-pill " + (ok ? "" : "offline");
  $("server-text").textContent = ok ? "已连接" : "连接中断";
  $("net-banner").classList.toggle("hidden", ok);
}

async function pollComfy() {
  try {
    const d = await getJSON("/api/comfy-status", 8000);
    $("comfy-dot").className = "dot " + (d.ok ? "online" : "offline");
    $("comfy-text").textContent = (d.ok ? "ComfyUI 在线 · " : "ComfyUI 离线 · ")
      + (d.address || "");
    $("comfy-line").title = d.error || "";
  } catch (e) {
    $("comfy-dot").className = "dot offline";
    $("comfy-text").textContent = "ComfyUI 状态未知";
  }
}

/* ---------------- 日志 ---------------- */

function initLogEmpty() {
  const lines = $("log-lines");
  if (lines.children.length === 0) {
    const empty = document.createElement("div");
    empty.className = "log-empty";
    empty.id = "log-empty";
    empty.textContent = "暂无日志。开始处理后，每张图片的进度与结果会显示在这里。";
    lines.appendChild(empty);
  }
}

function appendLogs(lines) {
  if (!lines || !lines.length) return;
  const box = $("log-box");
  const list = $("log-lines");
  const atBottom = box.scrollHeight - box.scrollTop - box.clientHeight < 30;
  const empty = $("log-empty");
  if (empty) empty.remove();
  for (const line of lines) {
    const row = document.createElement("div");
    row.className = "log-line " + (line.kind || "info");
    const time = document.createElement("span");
    time.className = "log-time";
    time.textContent = fmtTime(line.t);
    const text = document.createElement("span");
    text.className = "log-text";
    text.textContent = line.text;
    row.append(time, text);
    list.appendChild(row);
  }
  while (list.children.length > 800) list.removeChild(list.firstChild);
  if (atBottom) box.scrollTop = box.scrollHeight;
}

function clearLogDisplay() {
  $("log-lines").innerHTML = "";
  initLogEmpty();
}

/* ---------------- 对比组浏览 ---------------- */

async function pollPairs() {
  await refreshPairState(false);
  setTimeout(pollPairs, document.hidden ? 4200 : 1600);
}

async function refreshPairState(force = false) {
  if (!state.viewer.job) {
    updateStageInfo(null);
    if (!state.viewing) renderEmpty("选择输出文件夹后，这里会自动显示对比图");
    updateNavButtons([], -1);
    return;
  }
  const jobNow = state.viewer.job;
  try {
    const d = await getJSON(
      `/api/state?root=${encodeURIComponent(state.viewer.root)}`
      + `&job=${encodeURIComponent(state.viewer.job)}`, 12000);
    if (jobNow !== state.viewer.job) return; // 期间切换了任务文件夹
    state.pairState = d;
    updateStageInfo(d);
    if (state.follow) {
      const latest = d.latest;
      if (!latest) {
        renderEmpty();
        state.lastPairKey = "";
      } else {
        const key = `${latest.name}@${Math.round(latest.max_mtime || 0)}`;
        if (force || key !== state.lastPairKey) {
          state.lastPairKey = key;
          renderPair(latest, { flash: !force });
          updateNavFromCache();
        }
      }
    }
  } catch (e) {
    updateStageInfo(null);
  }
}

function updateStageInfo(d) {
  const job = state.viewer.job;
  let text = "未选择对比图目录";
  let count = 0;
  if (job && d) {
    if (!d.exists) {
      text = "任务文件夹不存在或已被删除";
    } else if (!d.count) {
      text = "共 0 组对比图 · 等待处理输出…";
    } else {
      count = d.count;
      text = `共 ${d.count} 组 · 最新 ${d.latest ? d.latest.name : "—"}`
        + ` · 更新于 ${d.latest ? fmtTime(d.latest.max_mtime) : "—"}`;
    }
  } else if (job) {
    text = "正在读取对比图…";
  }
  $("stage-info").textContent = text;
  $("stage-info").title = text;
  $("pair-badge").textContent = String(count);

  const now = new Date();
  $("status-bar").textContent = job
    ? `${text} · 扫描 ${fmtClock(now)} · ↑↓ 切换 · Tab 沉浸`
    : "先在左侧选择输出文件夹，或指定一个包含 control/ 与 target/ 的目录";
}

function renderPair(pair, { flash = true } = {}) {
  state.viewing = pair;
  renderSide("input", "control", pair);
  renderSide("output", "target", pair);
  $("meta-input").textContent = pair.name + (pair.control_mtime ? " · " + fmtTime(pair.control_mtime) : "");
  $("meta-output").textContent = pair.name + (pair.target_mtime ? " · " + fmtTime(pair.target_mtime) : "");
  updateNavFromCache();
  if (flash) flashCompare();
}

function renderSide(id, side, pair) {
  const img = $("img-" + id);
  const ph = $("ph-" + id);
  const has = pair["has_" + side];
  if (has) {
    ph.classList.add("hidden");
    img.classList.remove("hidden");
    img.onerror = () => {
      img.classList.add("hidden");
      ph.textContent = "图片加载失败";
      ph.classList.remove("hidden");
    };
    img.onload = () => {
      img.classList.remove("hidden");
      ph.classList.add("hidden");
    };
    img.src = imgURL(state.viewer.job, side, pair[side + "_name"], pair[side + "_mtime"]);
  } else {
    img.classList.add("hidden");
    img.removeAttribute("src");
    ph.textContent = side === "control" ? "原图缺失" : "生成图缺失";
    ph.classList.remove("hidden");
  }
}

function renderEmpty(msg) {
  state.viewing = null;
  for (const id of ["input", "output"]) {
    const img = $("img-" + id);
    img.classList.add("hidden");
    img.removeAttribute("src");
    const ph = $("ph-" + id);
    ph.textContent = msg || "等待处理…暂无图片";
    ph.classList.remove("hidden");
  }
  $("meta-input").textContent = "—";
  $("meta-output").textContent = "—";
  updateNavButtons([], -1);
}

function flashCompare() {
  const cmp = $("compare");
  cmp.classList.remove("flash");
  void cmp.offsetWidth;
  cmp.classList.add("flash");
  setTimeout(() => cmp.classList.remove("flash"), 1100);
}

async function ensurePairs(force = false) {
  if (!state.viewer.job) return [];
  const now = Date.now();
  if (!force && state.pairs && state.pairsJob === state.viewer.job && now - state.pairsAt < 2500) {
    return state.pairs;
  }
  const jobNow = state.viewer.job;
  try {
    const d = await getJSON("/api/pairs?job=" + encodeURIComponent(state.viewer.job));
    if (jobNow !== state.viewer.job) return state.pairs || [];
    state.pairs = d.pairs || [];
    state.pairsJob = state.viewer.job;
    state.pairsAt = now;
    $("drawer-count").textContent = String(state.pairs.length);
    return state.pairs;
  } catch (e) {
    return state.pairs || [];
  }
}

/** 与原查看器一样：未手动指定目录时，定期跟随输出文件夹 */
async function autoFollowOutput() {
  if (state.viewer.manual || state.phase !== "idle") return;
  try {
    const d = await getJSON("/api/autodetect", 6000);
    if (!d.ok || !d.root) return;
    if (d.root === state.viewer.root) return;
    setViewerRoot(d.root, d.job || d.root, false);
    await loadJobs(d.job || d.root, { quiet: true });
  } catch (e) { /* 服务暂不可用，静默重试 */ }
}

function updateNavButtons(pairs, idx) {
  const has = Array.isArray(pairs) && pairs.length > 0;
  $("btn-prev").disabled = !has || idx <= 0;
  $("edge-prev").disabled = !has || idx <= 0;
  $("btn-next").disabled = !has || idx >= pairs.length - 1;
  $("edge-next").disabled = !has || idx >= pairs.length - 1;
}

function updateNavFromCache() {
  if (!state.pairs || state.pairsJob !== state.viewer.job) return;
  if (!state.viewing) {
    updateNavButtons(state.pairs, -1);
    return;
  }
  const idx = state.pairs.findIndex((p) => p.name === state.viewing.name);
  updateNavButtons(state.pairs, idx);
}

async function navigate(offset) {
  if (!state.viewer.job) return toast("请先选择对比图目录", "err");
  // 优先用短缓存，键盘连续切换时不必每次都重新扫描整个目录
  const pairs = await ensurePairs(false);
  if (!pairs.length) {
    updateNavButtons([], -1);
    return toast("暂无可浏览的对比图", "warn");
  }
  let idx = state.viewing
    ? pairs.findIndex((p) => p.name === state.viewing.name)
    : -1;
  if (idx < 0) idx = 0;
  idx = Math.max(0, Math.min(pairs.length - 1, idx + offset));
  renderPair(pairs[idx]);
  updateNavButtons(pairs, idx);
  setFollow(false);
}

function setFollow(on) {
  state.follow = !!on;
  $("chk-follow").checked = state.follow;
}

function initFitMode() {
  let saved = null;
  try { saved = localStorage.getItem("a2r_fit_mode"); } catch (e) { /* ignore */ }
  setFitMode(saved === "cover" ? "cover" : "contain", false);
  document.querySelectorAll("[data-fit]").forEach((btn) => {
    btn.addEventListener("click", () => setFitMode(btn.dataset.fit));
  });
}

function setFitMode(mode, persist = true) {
  const fit = mode === "cover" ? "cover" : "contain";
  $("compare").dataset.fit = fit;
  document.querySelectorAll("[data-fit]").forEach((btn) => {
    const active = btn.dataset.fit === fit;
    btn.classList.toggle("active", active);
    btn.setAttribute("aria-pressed", active ? "true" : "false");
  });
  if (persist) {
    try { localStorage.setItem("a2r_fit_mode", fit); } catch (e) { /* ignore */ }
  }
}

/* ---------------- 对比组抽屉 ---------------- */

function setDrawerInert(inert) {
  const drawer = $("drawer");
  drawer.inert = !!inert;
  if (inert) drawer.setAttribute("aria-hidden", "true");
  else drawer.removeAttribute("aria-hidden");
}

async function openDrawer() {
  closeSidebar({ keepScrim: true });
  state.drawerOpen = true;
  $("drawer").classList.add("open");
  setDrawerInert(false);
  updateScrim();
  $("pair-list").innerHTML = '<div class="drawer-empty">加载中…</div>';
  const pairs = await ensurePairs(true);
  renderPairList(pairs);
  setTimeout(() => $("pair-search").focus(), 240);
}

function closeDrawer() {
  state.drawerOpen = false;
  $("drawer").classList.remove("open");
  setDrawerInert(true);
  updateScrim();
}

function renderPairList(pairs) {
  const box = $("pair-list");
  const q = $("pair-search").value.trim().toLowerCase();
  const filtered = (pairs || []).filter((p) => !q || p.name.toLowerCase().includes(q));
  $("drawer-count").textContent = q
    ? `${filtered.length}/${(pairs || []).length}`
    : String((pairs || []).length);
  if (!filtered.length) {
    box.innerHTML = `<div class="drawer-empty">${q ? "没有匹配的文件名" : "暂无对比图"}</div>`;
    return;
  }
  const frag = document.createDocumentFragment();
  for (const p of filtered) {
    const item = document.createElement("button");
    item.type = "button";
    item.className = "pair-item" + (state.viewing && state.viewing.name === p.name ? " active" : "");
    const inThumb = p.has_control
      ? `<span class="thumb in"><img loading="lazy" decoding="async" src="${imgURL(state.viewer.job, "control", p.control_name, p.control_mtime)}" alt=""></span>`
      : '<span class="thumb missing">缺</span>';
    const outThumb = p.has_target
      ? `<span class="thumb out"><img loading="lazy" decoding="async" src="${imgURL(state.viewer.job, "target", p.target_name, p.target_mtime)}" alt=""></span>`
      : '<span class="thumb missing">缺</span>';
    const chipC = p.has_control ? '<span class="chip ok">原✓</span>' : '<span class="chip miss">原缺</span>';
    const chipT = p.has_target ? '<span class="chip ok">生✓</span>' : '<span class="chip miss">生缺</span>';
    item.innerHTML = `
      <span class="pair-thumbs">${inThumb}${outThumb}</span>
      <span class="pair-info">
        <span class="pair-name" title="${esc(p.name)}">${esc(p.name)}</span>
        <span class="pair-time">${fmtTime(p.max_mtime, true)}</span>
        <span class="chips">${chipC}${chipT}</span>
      </span>`;
    item.addEventListener("click", () => {
      renderPair(p);
      setFollow(false);
      closeDrawer();
    });
    frag.appendChild(item);
  }
  box.innerHTML = "";
  box.appendChild(frag);
}

/* ---------------- 浏览目录 / 任务文件夹 ---------------- */

function setViewerRoot(root, job, manual) {
  state.viewer.root = root || "";
  state.viewer.job = job || "";
  state.viewer.manual = !!manual;
  state.pairs = null;
  state.pairsJob = null;
  state.viewing = null;
  state.lastPairKey = "";
  updateBrowseUI();
}

function updateBrowseUI() {
  $("browse-root").textContent = state.viewer.root || "—";
  $("browse-root").title = state.viewer.root || "";
  const tag = $("browse-mode");
  tag.textContent = state.viewer.manual ? "手动目录" : "自动跟随";
  tag.classList.toggle("manual", !!state.viewer.manual);
  $("btn-browse-output").disabled = !$("out-folder").value.trim();
}

async function persistViewer() {
  try {
    await postJSON("/api/save", {
      root: state.viewer.root,
      job: state.viewer.job,
      manual: state.viewer.manual,
    }, 8000);
  } catch (e) { /* 浏览状态不是关键数据 */ }
}

async function loadJobs(prefer, { quiet = false } = {}) {
  const root = state.viewer.root;
  if (!root) {
    state.jobs = [];
    $("sel-job").innerHTML = "";
    const o = document.createElement("option");
    o.value = "";
    o.textContent = "（未选择目录）";
    $("sel-job").appendChild(o);
    updateStageInfo(null);
    renderEmpty("选择输出文件夹后，这里会自动显示对比图");
    return;
  }
  let d = null;
  try {
    d = await getJSON("/api/jobs?root=" + encodeURIComponent(root));
  } catch (e) {
    if (!quiet) toast("读取任务文件夹失败", "err");
    return;
  }
  state.jobs = d.jobs || [];
  const sel = $("sel-job");
  sel.innerHTML = "";
  if (!state.jobs.length) {
    const o = document.createElement("option");
    o.value = "";
    o.textContent = "（未找到任务文件夹）";
    sel.appendChild(o);
    state.viewer.job = "";
    updateStageInfo(null);
    renderEmpty("该目录下还没有 control/ 或 target/ 文件夹");
    return;
  }
  for (const j of state.jobs) {
    const o = document.createElement("option");
    o.value = j;
    o.textContent = j === root ? "（根目录本身）" : j.split(/[\\/]/).filter(Boolean).pop();
    o.title = j;
    sel.appendChild(o);
  }
  const pick = prefer && state.jobs.includes(prefer) ? prefer : state.jobs[0];
  sel.value = pick;
  state.viewer.job = pick;
  updateBrowseUI();
  state.pairs = null;
  state.pairsJob = null;
  state.viewing = null;
  state.lastPairKey = "";
  await refreshPairState(true);
  await ensurePairs(true);
  updateNavFromCache();
}

/* ---------------- 目录选择弹窗 ---------------- */

function openDirModal(target) {
  state.dirTarget = target;
  state.dirOpen = true;
  const titles = {
    input: "选择输入文件夹",
    output: "选择输出文件夹",
    browse: "选择对比图根目录",
  };
  $("dir-modal-title").textContent = titles[target] || "选择文件夹";
  const current = target === "input" ? $("in-folder").value.trim()
    : target === "output" ? $("out-folder").value.trim()
      : state.viewer.root;
  state.modalPath = current || "";
  $("dir-modal").classList.remove("hidden");
  updateScrim();
  loadDirs();
}

function closeDirModal() {
  state.dirOpen = false;
  state.dirTarget = null;
  $("dir-modal").classList.add("hidden");
  updateScrim();
}

async function loadDirs() {
  const list = $("dir-list");
  list.innerHTML = '<div class="dir-empty">加载中…</div>';
  try {
    const d = await getJSON("/api/dirs?path=" + encodeURIComponent(state.modalPath || ""));
    if (!d.ok) {
      $("dir-path").textContent = state.modalPath || "请选择磁盘";
      list.innerHTML = `<div class="dir-empty">${esc(d.error || "目录不存在")}</div>`;
      $("btn-dir-parent").disabled = !parentPath(state.modalPath);
      $("btn-dir-choose").disabled = true;
      return;
    }
    state.modalPath = d.path || "";
    $("dir-path").textContent = state.modalPath || "请选择磁盘";
    $("btn-dir-choose").disabled = !state.modalPath;
    $("btn-dir-parent").disabled = !d.parent;
    list.innerHTML = "";
    if (!d.entries.length) {
      list.innerHTML = '<div class="dir-empty">（空文件夹）</div>';
      return;
    }
    for (const entry of d.entries) {
      const item = document.createElement("div");
      item.className = "dir-item" + (d.drive ? " drive" : "");
      item.textContent = d.drive ? entry : "📁 " + entry;
      item.addEventListener("click", () => {
        state.modalPath = d.drive ? entry : joinPath(state.modalPath, entry);
        loadDirs();
      });
      list.appendChild(item);
    }
  } catch (e) {
    list.innerHTML = '<div class="dir-empty">读取目录失败</div>';
  }
}

function joinPath(a, b) {
  if (!a) return b;
  return a.replace(/[\\/]+$/, "") + "\\" + b;
}

function parentPath(p) {
  p = (p || "").replace(/[\\/]+$/, "");
  if (!p) return "";
  if (/^[A-Za-z]:$/.test(p)) return "";
  const i = Math.max(p.lastIndexOf("\\"), p.lastIndexOf("/"));
  return i < 0 ? "" : p.slice(0, i);
}

function chooseDir() {
  if (!state.modalPath) return;
  const path = state.modalPath;
  const target = state.dirTarget;
  closeDirModal();
  if (target === "input") {
    $("in-folder").value = path;
    refreshInputCount();
    saveSoon();
  } else if (target === "output") {
    $("out-folder").value = path;
    onOutputCommitted();
  } else if (target === "browse") {
    setViewerRoot(path, path, true);
    persistViewer();
    loadJobs(path);
  }
}

function onOutputCommitted() {
  saveSoon();
  updateBrowseUI();
  const out = $("out-folder").value.trim();
  if (!out) return;
  if (!state.viewer.manual) {
    setViewerRoot(out, out, false);
    persistViewer();
    loadJobs(out, { quiet: true });
  }
}

/* ---------------- 提示词预设 ---------------- */

function renderPresets(target) {
  const box = $(target === "semi" ? "semi-presets" : "presets");
  const presets = (state.config && state.config.presets) || [];
  box.innerHTML = "";
  if (!presets.length) {
    box.innerHTML = '<span class="empty">暂无预设，输入提示词后点「存为预设」</span>';
    return;
  }
  for (const p of presets) {
    const chip = document.createElement("span");
    chip.className = "preset";
    chip.title = p;
    const label = document.createElement("button");
    label.type = "button";
    label.className = "preset-label";
    label.textContent = p;
    label.addEventListener("click", () => {
      if (target === "semi") {
        $("semi-prompt").value = p;
      } else {
        $("prompt").value = p;
        saveSoon();
      }
    });
    const del = document.createElement("button");
    del.type = "button";
    del.className = "preset-del";
    del.textContent = "×";
    del.title = "删除此预设";
    del.setAttribute("aria-label", `删除预设 ${p}`);
    del.addEventListener("click", (e) => {
      e.stopPropagation();
      deletePreset(p);
    });
    chip.append(label, del);
    box.appendChild(chip);
  }
}

async function addPreset(source) {
  const text = (source === "semi" ? $("semi-prompt").value : $("prompt").value).trim();
  if (!text) return toast("提示词为空，无法保存为预设", "warn");
  if ((state.config.presets || []).includes(text)) {
    return toast("这条预设已存在", "warn");
  }
  try {
    const d = await postJSON("/api/presets", { action: "add", text });
    if (!d.ok) return toast(d.error || "保存预设失败", "err");
    state.config.presets = d.presets;
    renderPresets("main");
    if (state.semiToken) renderPresets("semi");
    toast("已保存为预设", "ok", 2200);
  } catch (e) {
    toast("保存预设失败", "err");
  }
}

async function deletePreset(text) {
  if (!window.confirm(`删除预设「${text}」？`)) return;
  try {
    const d = await postJSON("/api/presets", { action: "delete", text });
    if (!d.ok) return toast(d.error || "删除失败", "err");
    state.config.presets = d.presets;
    renderPresets("main");
    if (state.semiToken) renderPresets("semi");
  } catch (e) {
    toast("删除预设失败", "err");
  }
}

/* ---------------- 半自动确认 ---------------- */

function openSemi(d) {
  const semi = d.semi;
  closeDrawer();
  closeSidebar();
  state.semiToken = semi.token;
  state.semiPrevFocus = document.activeElement;

  const completed = Math.min(Number(semi.next_index) || 0, Number(semi.total) || 0);
  const total = Number(semi.total) || 0;
  $("semi-title").textContent = completed >= total
    ? "全部图片已完成"
    : `第 ${completed}/${total} 张已完成`;
  const currentName = (semi.last_result && semi.last_result.input_name)
    || (d.last_result && d.last_result.input_name) || "";
  $("semi-subtitle").textContent = currentName
    ? `本次完成：${currentName} · 提示词修改会用于重新生成或后续图片`
    : "检查本次结果，决定下一步；提示词修改会用于重新生成或后续图片";
  $("semi-stats").textContent = `成功 ${d.success} · 失败 ${d.fail}`;

  $("semi-prompt").value = semi.prompt || "";
  renderPresets("semi");

  const result = semi.last_result || d.last_result;
  const outputFolder = d.output_folder
    || (state.settings && state.settings.output_folder) || "";
  const empty = $("semi-result-empty");
  const figIn = $("semi-fig-in");
  const figOut = $("semi-fig-out");
  $("semi-img-in").onerror = () => figIn.classList.add("hidden");
  $("semi-img-out").onerror = () => figOut.classList.add("hidden");
  if (result && result.ok && result.output_name) {
    figIn.classList.remove("hidden");
    figOut.classList.remove("hidden");
    empty.classList.add("hidden");
    if (result.control_name) {
      $("semi-img-in").src = imgURL(outputFolder, "control", result.control_name, result.control_mtime);
      $("semi-cap-in").textContent = `原图 · ${result.control_name}`;
      figIn.classList.remove("hidden");
    } else {
      figIn.classList.add("hidden");
    }
    $("semi-img-out").src = imgURL(outputFolder, "target", result.output_name, result.output_mtime);
    $("semi-cap-out").textContent = `生成图 · ${result.output_name}`;
    figOut.classList.remove("hidden");
  } else {
    figIn.classList.add("hidden");
    figOut.classList.add("hidden");
    empty.classList.remove("hidden");
    empty.textContent = result
      ? `本次生成失败：${result.message || "未知错误"}`
      : "本次没有生成结果";
  }

  const nextFile = semi.next_file || "";
  const nextImg = $("semi-next-img");
  if (nextFile) {
    nextImg.onerror = () => {
      nextImg.classList.add("hidden");
      $("semi-next-empty").textContent = "预览加载失败";
      $("semi-next-empty").classList.remove("hidden");
    };
    nextImg.src = inputImgURL(nextFile, semi.next_mtime);
    nextImg.classList.remove("hidden");
    $("semi-next-empty").classList.add("hidden");
    $("semi-next-name").textContent = nextFile;
    $("semi-next-after").textContent = semi.after_file
      ? `之后：${semi.after_file}`
      : "这是最后一张";
  } else {
    nextImg.removeAttribute("src");
    nextImg.classList.add("hidden");
    $("semi-next-empty").textContent = "没有更多图片";
    $("semi-next-empty").classList.remove("hidden");
    $("semi-next-name").textContent = "—";
    $("semi-next-after").textContent = "没有更多待处理的图片";
  }

  $("btn-semi-next").textContent = completed >= total
    ? "✓ 完成并结束"
    : "✓ 满意，下一张";
  setSemiButtonsDisabled(false);

  $("semi-modal").classList.remove("hidden");
  updateScrim();
  setTimeout(() => $("semi-card").focus(), 40);
}

function closeSemi() {
  state.semiToken = null;
  $("semi-modal").classList.add("hidden");
  updateScrim();
  if (state.semiPrevFocus && document.contains(state.semiPrevFocus)) {
    try { state.semiPrevFocus.focus(); } catch (e) { /* ignore */ }
  }
  state.semiPrevFocus = null;
}

function setSemiButtonsDisabled(disabled) {
  for (const id of ["btn-semi-retry", "btn-semi-next", "btn-semi-stop"]) {
    $(id).disabled = disabled;
  }
}

async function semiDecide(action) {
  if (!state.semiToken) return;
  const prompt = $("semi-prompt").value;
  setSemiButtonsDisabled(true);
  try {
    const d = await postJSON("/api/semi", { action, prompt });
    if (!d.ok) {
      setSemiButtonsDisabled(false);
      return toast(d.error || "提交失败", "err");
    }
    // 防止轮询在后台清掉 waiting 之前把弹窗重新打开
    state.suppressSemiToken = state.semiToken;
    // 与原逻辑一致：对话框里的提示词会写回主界面
    $("prompt").value = prompt;
    if (state.settings) state.settings.prompt = prompt;
    closeSemi();
    if (action === "retry") toast("正在重新生成当前图片…", "warn");
    else if (action === "next") toast("继续下一张", "ok", 2000);
    else toast("正在停止…", "warn");
    pollStatusNow();
  } catch (e) {
    setSemiButtonsDisabled(false);
    toast("提交失败，请检查服务端连接", "err");
  }
}

/* ---------------- 侧栏 / 抽屉 / 遮罩 / 沉浸 ---------------- */

function isNarrow() {
  return window.matchMedia("(max-width: 1180px)").matches;
}

/** 移动端收起的侧栏不应进入焦点/读屏顺序 */
function syncSidebarInert() {
  const sidebar = $("sidebar");
  const hidden = isNarrow() && !sidebar.classList.contains("open")
    && !document.body.classList.contains("immersive");
  sidebar.inert = hidden;
  if (hidden) sidebar.setAttribute("aria-hidden", "true");
  else sidebar.removeAttribute("aria-hidden");
}

function openSidebar() {
  if (isNarrow()) {
    closeDrawer();
    state.sidebarOpen = true;
    $("sidebar").classList.add("open");
    syncSidebarInert();
    updateScrim();
  } else {
    document.body.classList.remove("rail-collapsed");
  }
}

function closeSidebar({ keepScrim = false } = {}) {
  state.sidebarOpen = false;
  $("sidebar").classList.remove("open");
  syncSidebarInert();
  if (!keepScrim) updateScrim();
}

function toggleSidebar() {
  if (isNarrow()) {
    if ($("sidebar").classList.contains("open")) closeSidebar();
    else openSidebar();
  } else {
    document.body.classList.toggle("rail-collapsed");
  }
}

function updateScrim() {
  const any = state.sidebarOpen || state.drawerOpen;
  $("scrim").classList.toggle("show", any);
  document.body.classList.toggle("modal-open", any || state.dirOpen || !!state.semiToken);
}

function toggleImmersive(force) {
  const next = force == null ? !state.immersive : !!force;
  state.immersive = next;
  document.body.classList.toggle("immersive", next);
  $("btn-immersive-exit").classList.toggle("hidden", !next);
}

/* ---------------- 事件绑定 ---------------- */

function bindEvents() {
  // 顶栏
  $("btn-sidebar").addEventListener("click", toggleSidebar);
  $("btn-sidebar-close").addEventListener("click", () => closeSidebar());
  $("btn-drawer").addEventListener("click", () => {
    if (state.drawerOpen) closeDrawer();
    else openDrawer();
  });
  $("btn-drawer-close").addEventListener("click", closeDrawer);
  $("btn-drawer-refresh").addEventListener("click", async () => {
    const pairs = await ensurePairs(true);
    renderPairList(pairs);
  });
  $("pair-search").addEventListener("input", () => {
    renderPairList(state.pairs || []);
  });
  $("btn-immersive").addEventListener("click", () => toggleImmersive());
  $("btn-immersive-exit").addEventListener("click", () => toggleImmersive(false));
  $("scrim").addEventListener("click", () => {
    closeDrawer();
    closeSidebar();
  });

  // 文件夹
  for (const btn of document.querySelectorAll("[data-browse]")) {
    btn.addEventListener("click", () => openDirModal(btn.dataset.browse));
  }
  $("in-folder").addEventListener("input", () => {
    clearTimeout(state.folderTimer);
    state.folderTimer = setTimeout(refreshInputCount, 400);
    saveSoon();
  });
  $("in-folder").addEventListener("change", () => {
    clearTimeout(state.folderTimer);
    refreshInputCount();
    saveSoon();
  });
  $("out-folder").addEventListener("input", () => {
    saveSoon();
    updateBrowseUI();
  });
  $("out-folder").addEventListener("change", onOutputCommitted);
  for (const id of ["in-folder", "out-folder"]) {
    $(id).addEventListener("keydown", (e) => {
      if (e.key === "Enter") $(id).blur();
    });
  }

  // 提示词
  $("prompt").addEventListener("input", saveSoon);
  $("btn-add-preset").addEventListener("click", () => addPreset("main"));

  // 模型与参数
  $("mode").addEventListener("change", () => {
    $("rail-mode-label").textContent = $("mode").value;
    saveSoon();
  });
  $("workflow").addEventListener("change", () => {
    applyWorkflowUI({ preferSaved: false });
    saveSoon();
  });
  $("lora").addEventListener("change", saveSoon);
  $("checkpoint").addEventListener("change", saveSoon);
  $("strength").addEventListener("change", saveSoon);
  $("steps").addEventListener("change", saveSoon);
  $("cfg").addEventListener("change", saveSoon);
  $("resize").addEventListener("change", saveSoon);
  $("start-index").addEventListener("input", () => {
    updateFolderHints();
    saveSoon();
  });
  $("start-index").addEventListener("change", () => {
    updateFolderHints();
    saveSoon();
  });
  $("btn-refresh-lora").addEventListener("click", () => refreshModels("lora"));
  $("btn-refresh-checkpoint").addEventListener("click", () => refreshModels("checkpoint"));

  // 运行
  $("btn-start").addEventListener("click", startRun);
  $("btn-pause").addEventListener("click", pauseRun);
  $("btn-resume").addEventListener("click", resumeRun);
  $("btn-stop").addEventListener("click", stopRun);
  $("dock-action").addEventListener("click", () => {
    if (state.phase === "running") pauseRun();
    else if (state.phase === "paused") resumeRun();
    else if (state.phase === "idle") startRun();
  });
  $("dock-open").addEventListener("click", openSidebar);

  // 日志
  $("btn-log-toggle").addEventListener("click", () => {
    state.logCollapsed = !state.logCollapsed;
    const box = $("log-box");
    box.classList.toggle("collapsed", state.logCollapsed);
    $("btn-log-toggle").textContent = state.logCollapsed ? "展开" : "收起";
    if (!state.logCollapsed) {
      requestAnimationFrame(() => { box.scrollTop = box.scrollHeight; });
    }
  });
  $("btn-log-clear").addEventListener("click", clearLogDisplay);

  // 对比图
  $("btn-prev").addEventListener("click", () => navigate(-1));
  $("btn-next").addEventListener("click", () => navigate(1));
  $("edge-prev").addEventListener("click", () => navigate(-1));
  $("edge-next").addEventListener("click", () => navigate(1));
  $("btn-pairs-refresh").addEventListener("click", async () => {
    if (!state.viewer.job) return toast("请先选择对比图目录", "err");
    await refreshPairState(true);
    ensurePairs(true);
    updateNavFromCache();
  });
  $("chk-follow").addEventListener("change", () => {
    state.follow = $("chk-follow").checked;
    if (state.follow) {
      state.lastPairKey = "";
      refreshPairState(true);
      ensurePairs(true);
    }
  });
  $("sel-job").addEventListener("change", async () => {
    state.viewer.job = $("sel-job").value || "";
    state.pairs = null;
    state.pairsJob = null;
    state.viewing = null;
    state.lastPairKey = "";
    persistViewer();
    await refreshPairState(true);
    await ensurePairs(true);
    updateNavFromCache();
  });
  $("btn-jobs-refresh").addEventListener("click", () => loadJobs(state.viewer.job));
  $("btn-choose-root").addEventListener("click", () => openDirModal("browse"));
  $("btn-browse-output").addEventListener("click", () => {
    const out = $("out-folder").value.trim();
    if (!out) return toast("还没有设置输出文件夹", "warn");
    setViewerRoot(out, out, false);
    persistViewer();
    loadJobs(out);
  });

  // 重新读取磁盘上的参数状态
  $("btn-reload").addEventListener("click", async () => {
    if (state.phase !== "idle") return toast("处理中不能重新读取参数", "warn");
    clearTimeout(state.saveTimer);
    state.saveTimer = null;
    try {
      const cfg = await getJSON("/api/config?reload=1", 20000);
      applyConfig(cfg);
      closeSemi();
      toast("已重新读取保存的参数", "ok");
    } catch (e) {
      toast("读取失败，请检查连接", "err");
    }
  });

  // 目录弹窗
  $("btn-dir-close").addEventListener("click", closeDirModal);
  $("btn-dir-parent").addEventListener("click", () => {
    state.modalPath = parentPath(state.modalPath);
    loadDirs();
  });
  $("btn-dir-choose").addEventListener("click", chooseDir);
  $("dir-modal").addEventListener("click", (e) => {
    if (e.target === $("dir-modal")) closeDirModal();
  });

  // 半自动
  $("btn-semi-retry").addEventListener("click", () => semiDecide("retry"));
  $("btn-semi-next").addEventListener("click", () => semiDecide("next"));
  $("btn-semi-stop").addEventListener("click", () => semiDecide("stop"));

  // 键盘
  document.addEventListener("keydown", (e) => {
    if (e.isComposing || e.defaultPrevented) return;

    if (e.key === "Escape") {
      if (state.dirOpen) { closeDirModal(); return; }
      if (state.drawerOpen) { closeDrawer(); return; }
      if (state.sidebarOpen) { closeSidebar(); return; }
      if (state.immersive) { toggleImmersive(false); return; }
    }

    // Tab 切换沉浸模式（输入框、弹窗、抽屉内保持原生 Tab 焦点导航）
    if (e.key === "Tab"
        && !e.altKey && !e.ctrlKey && !e.metaKey && !e.shiftKey
        && !isEditable(e.target)
        && !state.dirOpen && !state.semiToken
        && !state.drawerOpen && !state.sidebarOpen) {
      e.preventDefault();
      toggleImmersive();
      return;
    }

    // ↑ / ↓ 切换上一对 / 下一对
    if ((e.key === "ArrowUp" || e.key === "ArrowDown")
        && !e.altKey && !e.ctrlKey && !e.metaKey && !e.shiftKey
        && !isEditable(e.target)
        && !state.dirOpen && !state.semiToken && !state.drawerOpen) {
      if (!state.viewer.job) return;
      e.preventDefault();
      if (state.pairState && state.pairState.count === 0) return;
      // 长按连发时限流，避免每帧都重新扫描/加载
      const now = Date.now();
      if (now - state.navLast < 140) return;
      state.navLast = now;
      navigate(e.key === "ArrowUp" ? -1 : 1);
      return;
    }

    if ((e.ctrlKey || e.metaKey) && (e.key === "b" || e.key === "B")
        && !isEditable(e.target)) {
      e.preventDefault();
      toggleSidebar();
    }
  });

  window.addEventListener("resize", () => {
    if (!isNarrow()) closeSidebar();
    syncSidebarInert();
    updateFolderHints();
  });

  initFitMode();

  if (window.innerWidth < 900) {
    state.logCollapsed = true;
    $("log-box").classList.add("collapsed");
    $("btn-log-toggle").textContent = "展开";
  }
}

async function refreshModels(kind) {
  try {
    let url;
    if (kind === "lora") {
      const wf = currentWorkflow();
      if (!wf || !wf.has_lora) return;
      url = `/api/models?kind=lora&workflow=${encodeURIComponent(wf.name)}&force=1`;
    } else {
      url = "/api/models?kind=checkpoint&force=1";
    }
    const d = await getJSON(url, 20000);
    if (!d.ok) return toast(d.error || "刷新失败", "err");
    if (kind === "lora") {
      state.config.loras[d.workflow] = d.files;
      if (d.warning) state.config.lora_warnings[d.workflow] = d.warning;
      else delete state.config.lora_warnings[d.workflow];
    } else {
      state.config.checkpoints = d.files;
      state.config.checkpoint_warning = d.warning || "";
    }
    applyWorkflowUI({ preferSaved: true });
    saveSoon();
    if (d.warning) toast(d.warning, "warn", 6000);
    else toast(`已刷新，共 ${d.files.length} 个模型`, "ok", 2400);
  } catch (e) {
    toast("刷新模型列表失败", "err");
  }
}

/* ---------------- 启动 ---------------- */

boot();
