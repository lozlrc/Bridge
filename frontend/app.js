const params = new URLSearchParams(window.location.search);
const storedApi = window.localStorage.getItem("bridge.api");
const paramApi = params.get("api");
const defaultApi =
  window.location.protocol.startsWith("http") && window.location.hostname
    ? `${window.location.protocol}//${window.location.hostname}:8000`
    : "http://localhost:8000";
const API = (paramApi || storedApi || defaultApi).replace(/\/$/, "");

if (paramApi) {
  window.localStorage.setItem("bridge.api", API);
}

const apiBadge = document.getElementById("api-badge");
const apiBadgeLabel = document.getElementById("api-badge-label");
const apiHint = document.getElementById("api-hint");
const summaryTextEl = document.getElementById("summary-text");
const resultSentencesEl = document.getElementById("result-sentences");
let apiHealth = null;
let currentPreviewUrl = null;

// ── Nav ───────────────────────────────────────────
function activateMode(mode) {
  document.querySelectorAll(".nav-item").forEach(item => {
    item.classList.toggle("active", item.dataset.mode === mode);
  });
  document.querySelectorAll(".panel").forEach(panel => {
    panel.classList.toggle("active", panel.id === `panel-${mode}`);
  });
  if (mode !== "image") stopCameraStream();
  hideOutput();
}

document.querySelectorAll(".nav-item").forEach(item => {
  item.addEventListener("click", () => activateMode(item.dataset.mode));
});

document.querySelectorAll("[data-jump]").forEach(button => {
  button.addEventListener("click", () => activateMode(button.dataset.jump));
});

// ── Output helpers ────────────────────────────────
function showSpinner() {
  document.getElementById("spinner").classList.remove("hidden");
  document.getElementById("result-box").classList.add("hidden");
  document.getElementById("error-msg").classList.add("hidden");
}

function hideOutput() {
  ["spinner", "result-box", "error-msg", "result-sentences"].forEach(id =>
    document.getElementById(id).classList.add("hidden")
  );
  summaryTextEl.classList.remove("hidden");
}

function showResult({ simple_text, simple_sentences, summary, mode }) {
  document.getElementById("spinner").classList.add("hidden");
  const outputText = simple_text || summary || "";
  const sentences = Array.isArray(simple_sentences)
    ? simple_sentences.filter(Boolean)
    : outputText
        .split(/(?<=[.!?])\s+/)
        .map(part => part.trim())
        .filter(Boolean);

  summaryTextEl.textContent = outputText;
  const inputLabel = mode === "image" ? "From image" : "From audio";
  const demoLabel = apiHealth?.demo_mode ? " · demo mode" : "";
  document.getElementById("result-meta").textContent =
    `${inputLabel} · essential only${demoLabel}`;

  if (sentences.length > 1) {
    resultSentencesEl.innerHTML = "";
    sentences.slice(0, 2).forEach((sentence, index) => {
      const item = document.createElement("li");
      item.className = "sentence-card";
      const idx = document.createElement("span");
      idx.className = "sentence-index";
      idx.textContent = String(index + 1);
      const copy = document.createElement("p");
      copy.className = "sentence-copy";
      copy.textContent = sentence;
      item.append(idx, copy);
      resultSentencesEl.appendChild(item);
    });
    summaryTextEl.classList.add("hidden");
    resultSentencesEl.classList.remove("hidden");
  } else {
    resultSentencesEl.innerHTML = "";
    resultSentencesEl.classList.add("hidden");
    summaryTextEl.classList.remove("hidden");
  }

  document.getElementById("result-box").classList.remove("hidden");
}

function showError(msg) {
  document.getElementById("spinner").classList.add("hidden");
  document.getElementById("error-text").textContent = msg;
  document.getElementById("error-msg").classList.remove("hidden");
}

function setBadge(state, label, hint) {
  apiBadge.className = `status-badge ${state}`;
  apiBadgeLabel.textContent = label;
  apiHint.textContent = hint;
}

async function updateBackendStatus() {
  try {
    const res = await fetch(`${API}/health`, { headers: { Accept: "application/json" } });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    apiHealth = await res.json();
    const summary = apiHealth.demo_mode
      ? "Demo fallbacks active. UI runs without every dependency."
      : "Live backend connected.";
    setBadge(
      apiHealth.demo_mode ? "demo" : "live",
      apiHealth.demo_mode ? "Demo API" : "Live API",
      summary
    );
  } catch (error) {
    apiHealth = null;
    setBadge("offline", "Backend offline", `Could not reach ${API}.`);
  }
}

async function fetchJson(url, options) {
  const res = await fetch(url, options);
  const raw = await res.text();
  let data = {};
  try {
    data = raw ? JSON.parse(raw) : {};
  } catch {
    data = { detail: raw || res.statusText };
  }
  if (!res.ok) {
    throw new Error(data.detail || res.statusText);
  }
  return data;
}

// ── Copy ─────────────────────────────────────────
const btnCopy = document.getElementById("btn-copy");
const btnCopyLabel = btnCopy.querySelector("span");
btnCopy.addEventListener("click", async () => {
  const sentences = Array.from(resultSentencesEl.querySelectorAll(".sentence-copy"))
    .map(el => el.textContent.trim());
  const text = sentences.length ? sentences.join(" ") : (summaryTextEl.textContent || "");
  if (!text) return;
  try {
    await navigator.clipboard.writeText(text);
    btnCopy.classList.add("copied");
    btnCopyLabel.textContent = "Copied";
    setTimeout(() => {
      btnCopy.classList.remove("copied");
      btnCopyLabel.textContent = "Copy";
    }, 1500);
  } catch (e) {
    // clipboard may be unavailable; ignore silently
  }
});

// ── Image mode ────────────────────────────────────
let cameraStream = null;
let capturedBlob = null;

const videoEl       = document.getElementById("camera-preview");
const canvasEl      = document.getElementById("camera-canvas");
const imgPreview    = document.getElementById("image-preview");
const placeholder   = document.getElementById("camera-placeholder");
const btnCamera     = document.getElementById("btn-start-camera");
const btnCameraLabel = document.getElementById("camera-button-label");
const btnCapture    = document.getElementById("btn-capture");
const btnClearImage = document.getElementById("btn-clear-image");
const btnTranslate  = document.getElementById("btn-translate-image");
const fileUpload    = document.getElementById("file-upload");

function showCameraView(el) {
  videoEl.classList.remove("active");
  imgPreview.classList.remove("active");
  placeholder.classList.add("hidden");
  el.classList.add("active");
}

function stopCameraStream() {
  cameraStream?.getTracks().forEach(track => track.stop());
  cameraStream = null;
  btnCapture.disabled = true;
}

function revokePreviewUrl() {
  if (currentPreviewUrl) {
    URL.revokeObjectURL(currentPreviewUrl);
    currentPreviewUrl = null;
  }
}

function resetImageState() {
  stopCameraStream();
  capturedBlob = null;
  revokePreviewUrl();
  imgPreview.removeAttribute("src");
  fileUpload.value = "";
  videoEl.classList.remove("active");
  imgPreview.classList.remove("active");
  placeholder.classList.remove("hidden");
  btnTranslate.disabled = true;
  btnClearImage.disabled = true;
  btnCameraLabel.textContent = "Start camera";
  hideOutput();
}

function loadImageBlob(blob) {
  capturedBlob = blob;
  revokePreviewUrl();
  currentPreviewUrl = URL.createObjectURL(blob);
  imgPreview.src = currentPreviewUrl;
  showCameraView(imgPreview);
  btnTranslate.disabled = false;
  btnClearImage.disabled = false;
  btnCameraLabel.textContent = "Restart camera";
}

btnCamera.addEventListener("click", async () => {
  try {
    hideOutput();
    stopCameraStream();
    capturedBlob = null;
    revokePreviewUrl();
    imgPreview.removeAttribute("src");
    btnTranslate.disabled = true;
    cameraStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
    videoEl.srcObject = cameraStream;
    showCameraView(videoEl);
    btnCapture.disabled = false;
    btnClearImage.disabled = false;
    btnCameraLabel.textContent = "Camera ready";
  } catch (e) {
    showError("Camera access denied: " + e.message);
  }
});

btnCapture.addEventListener("click", () => {
  canvasEl.width  = videoEl.videoWidth;
  canvasEl.height = videoEl.videoHeight;
  canvasEl.getContext("2d").drawImage(videoEl, 0, 0);
  canvasEl.toBlob(blob => {
    if (!blob) {
      showError("Could not capture an image.");
      return;
    }
    stopCameraStream();
    loadImageBlob(blob);
  }, "image/jpeg", 0.85);
});

fileUpload.addEventListener("change", () => {
  const file = fileUpload.files[0];
  if (!file) return;
  hideOutput();
  stopCameraStream();
  loadImageBlob(file);
});

btnClearImage.addEventListener("click", resetImageState);

btnTranslate.addEventListener("click", async () => {
  if (!capturedBlob) return;
  showSpinner();
  btnTranslate.disabled = true;
  const form = new FormData();
  form.append("file", capturedBlob, "image.jpg");
  try {
    const data = await fetchJson(`${API}/image`, { method: "POST", body: form });
    showResult(data);
  } catch (e) {
    showError("Error: " + e.message);
  } finally {
    btnTranslate.disabled = false;
  }
});

// ── Audio mode ────────────────────────────────────
let mediaRecorder = null;
let audioChunks   = [];
let audioBlob     = null;
let audioFilename = "recording.webm";

const btnRecord         = document.getElementById("btn-record");
const btnStop           = document.getElementById("btn-stop");
const btnClearAudio     = document.getElementById("btn-clear-audio");
const btnTranslateAudio = document.getElementById("btn-translate-audio");
const audioUpload       = document.getElementById("audio-upload");
const waveform          = document.getElementById("waveform");
const audioLabel        = document.getElementById("audio-label");

function resetAudioState() {
  if (mediaRecorder?.state === "recording") {
    try { mediaRecorder.stop(); } catch (_) {}
  }
  mediaRecorder = null;
  audioChunks = [];
  audioBlob = null;
  audioUpload.value = "";
  waveform.classList.remove("active", "loaded");
  audioLabel.textContent = "Press record or upload an audio file";
  btnRecord.disabled = false;
  btnStop.disabled = true;
  btnClearAudio.disabled = true;
  btnTranslateAudio.disabled = true;
  hideOutput();
}

function loadAudioBlob(blob, filename) {
  audioBlob = blob;
  audioFilename = filename;
  waveform.classList.remove("active");
  waveform.classList.add("loaded");
  audioLabel.textContent = `Audio loaded · ${filename}`;
  btnTranslateAudio.disabled = false;
  btnClearAudio.disabled = false;
}

btnRecord.addEventListener("click", async () => {
  try {
    if (!window.MediaRecorder) {
      throw new Error("This browser does not support in-browser audio recording.");
    }
    hideOutput();
    audioBlob = null;
    audioUpload.value = "";
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    audioChunks = [];
    mediaRecorder = new MediaRecorder(stream);

    mediaRecorder.ondataavailable = e => { if (e.data.size > 0) audioChunks.push(e.data); };
    mediaRecorder.onstop = () => {
      stream.getTracks().forEach(t => t.stop());
      const blob = new Blob(audioChunks, { type: "audio/webm" });
      loadAudioBlob(blob, "recording.webm");
      btnRecord.disabled = false;
      btnStop.disabled = true;
    };

    mediaRecorder.start(250);
    waveform.classList.remove("loaded");
    waveform.classList.add("active");
    audioLabel.textContent = "Recording…";
    btnRecord.disabled = true;
    btnStop.disabled = false;
    btnClearAudio.disabled = false;
    btnTranslateAudio.disabled = true;
  } catch (e) {
    showError("Audio setup failed: " + e.message);
  }
});

btnStop.addEventListener("click", () => {
  if (mediaRecorder?.state === "recording") mediaRecorder.stop();
  btnStop.disabled = true;
});

audioUpload.addEventListener("change", () => {
  const file = audioUpload.files[0];
  if (!file) return;
  hideOutput();
  if (mediaRecorder?.state === "recording") mediaRecorder.stop();
  loadAudioBlob(file, file.name);
});

btnClearAudio.addEventListener("click", resetAudioState);

btnTranslateAudio.addEventListener("click", async () => {
  if (!audioBlob) return;
  showSpinner();
  btnTranslateAudio.disabled = true;
  const form = new FormData();
  form.append("file", audioBlob, audioFilename);
  const previousLabel = audioLabel.textContent;
  audioLabel.textContent = "Processing audio…";
  try {
    const data = await fetchJson(`${API}/lecture`, { method: "POST", body: form });
    audioLabel.textContent = previousLabel;
    showResult(data);
  } catch (e) {
    audioLabel.textContent = previousLabel;
    showError("Error: " + e.message);
  } finally {
    btnTranslateAudio.disabled = false;
  }
});

window.addEventListener("beforeunload", () => {
  stopCameraStream();
  revokePreviewUrl();
});

updateBackendStatus();
