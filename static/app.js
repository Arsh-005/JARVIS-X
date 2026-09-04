const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

const chat = $("#chat");
const chatScroll = $("#chatScroll");
const promptInput = $("#prompt");
const sendButton = $("#send");
const fileInput = $("#fileInput");
const attachmentStrip = $("#attachmentStrip");
const dropZone = $("#dropZone");

let sessionId = crypto.randomUUID();
let selectedFiles = [];
let recognition = null;
let isListening = false;
let voiceEnabled = true;
let ragEnabled = false;
let agentEnabled = false;
let busy = false;


/* =========================================================
   FILE SETTINGS
========================================================= */

const MAX_FILE_SIZE = 25_000_000;
const MAX_ATTACHMENTS = 8;

const SUPPORTED_EXTENSIONS = [
  ".pdf",
  ".docx",
  ".txt",
  ".md",
  ".json",
  ".csv",
  ".py",
  ".js",
  ".ts",
  ".html",
  ".css",
  ".yaml",
  ".yml",
  ".xml",
];


/* =========================================================
   BASIC HELPERS
========================================================= */

function formatBytes(bytes) {
  if (bytes < 1024) {
    return `${bytes} B`;
  }

  if (bytes < 1024 ** 2) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }

  return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
}


function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}


function renderMarkdown(text) {
  const escaped = escapeHtml(text || "");

  const blocks = escaped.split(/```/);

  return blocks
    .map((block, index) => {

      if (index % 2 === 1) {

        const firstBreak = block.indexOf("\n");

        const language =
          firstBreak > -1
            ? block.slice(0, firstBreak).trim()
            : "code";

        const code =
          firstBreak > -1
            ? block.slice(firstBreak + 1)
            : block;

        return `
          <div class="code-block">

            <div class="code-head">

              <span>
                ${language || "code"}
              </span>

              <button
                class="copy-code"
                type="button"
              >
                Copy
              </button>

            </div>

            <pre><code>${code}</code></pre>

          </div>
        `;
      }

      return block
        .replace(
          /\*\*(.*?)\*\*/g,
          "<strong>$1</strong>"
        )
        .replace(
          /`([^`]+)`/g,
          "<code>$1</code>"
        )
        .split(/\n{2,}/)
        .map(
          (paragraph) =>
            `<p>${paragraph.replaceAll(
              "\n",
              "<br>"
            )}</p>`
        )
        .join("");
    })
    .join("");
}


function nowLabel() {
  return new Date().toLocaleTimeString(
    [],
    {
      hour: "2-digit",
      minute: "2-digit",
    }
  );
}


function showToast(
  message,
  type = "info"
) {

  const toast =
    document.createElement("div");

  toast.className =
    `toast ${
      type === "error"
        ? "error"
        : ""
    }`;

  toast.textContent = message;

  $("#toastStack").appendChild(toast);

  setTimeout(
    () => toast.remove(),
    4200
  );
}


function scrollToBottom() {

  requestAnimationFrame(() => {

    chatScroll.scrollTop =
      chatScroll.scrollHeight;

  });
}


function hideWelcome() {

  $("#welcome")
    ?.classList
    .add("hidden");

}


/* =========================================================
   CHAT MESSAGES
========================================================= */

function addMessage(
  role,
  text,
  files = []
) {

  hideWelcome();

  const item =
    document.createElement("article");

  item.className =
    `message ${
      role === "user"
        ? "user"
        : "assistant"
    }`;

  const avatarText =
    role === "user"
      ? "Y"
      : "JX";

  const name =
    role === "user"
      ? "You"
      : "JARVIS-X";


  const attachments =
    files.length
      ? `
        <div class="message-attachments">

          ${files
            .map(
              (file) => `
                <div class="message-file">

                  <span>
                    ${fileIcon(file)}
                  </span>

                  <div>

                    <b>
                      ${escapeHtml(file.name)}
                    </b>

                    <small>
                      ${formatBytes(file.size)}
                    </small>

                  </div>

                </div>
              `
            )
            .join("")}

        </div>
      `
      : "";


  item.innerHTML = `

    <div class="avatar">
      ${avatarText}
    </div>

    <div class="message-content">

      <div class="message-head">

        <b>
          ${name}
        </b>

        <span>
          ${nowLabel()}
        </span>

      </div>

      ${attachments}

      <div class="message-body">

        ${renderMarkdown(text)}

      </div>

    </div>
  `;


  chat.appendChild(item);


  item
    .querySelectorAll(".copy-code")
    .forEach((button) => {

      button.addEventListener(
        "click",
        async () => {

          const code =
            button
              .closest(".code-block")
              .querySelector("code")
              .textContent;

          await navigator.clipboard
            .writeText(code);

          button.textContent =
            "Copied";

          setTimeout(
            () => {
              button.textContent =
                "Copy";
            },
            1200
          );
        }
      );
    });


  scrollToBottom();

  return item;
}


/* =========================================================
   STATUS
========================================================= */

function setMiniStatus(
  text,
  state = "idle"
) {

  const status =
    $("#voiceStatus");

  status.textContent =
    text;

  status.dataset.state =
    state;
}


function setBusy(value) {

  busy = value;

  sendButton.disabled =
    value;

  sendButton.innerHTML =
    value
      ? "<span>…</span>"
      : "<span>↑</span>";
}


/* =========================================================
   FILE VALIDATION
========================================================= */

function getFileExtension(file) {

  const name =
    file.name.toLowerCase();

  const dotIndex =
    name.lastIndexOf(".");

  if (dotIndex < 0) {
    return "";
  }

  return name.slice(dotIndex);
}


function isSupportedFile(file) {

  /*
   * Images are intentionally disabled.
   */

  if (
    file.type.startsWith("image/")
  ) {
    return false;
  }


  /*
   * Audio remains supported.
   */

  if (
    file.type.startsWith("audio/")
  ) {
    return true;
  }


  /*
   * Video remains supported as upload/storage.
   */

  if (
    file.type.startsWith("video/")
  ) {
    return true;
  }


  const extension =
    getFileExtension(file);

  return SUPPORTED_EXTENSIONS
    .includes(extension);
}


function fileIcon(file) {

  if (
    file.type.startsWith("audio/")
  ) {
    return "◌";
  }


  if (
    file.type.startsWith("video/")
  ) {
    return "▷";
  }


  const name =
    file.name.toLowerCase();


  if (
    name.endsWith(".pdf")
  ) {
    return "PDF";
  }


  if (
    name.endsWith(".docx")
  ) {
    return "DOCX";
  }


  if (
    name.endsWith(".csv")
  ) {
    return "CSV";
  }


  return "◫";
}


/* =========================================================
   ATTACHMENT DISPLAY
========================================================= */

function renderAttachments() {

  attachmentStrip.innerHTML =
    "";

  attachmentStrip.hidden =
    selectedFiles.length === 0;


  selectedFiles.forEach(
    (file, index) => {

      const card =
        document.createElement("div");

      card.className =
        "attachment-card";


      const thumb =
        document.createElement("div");

      thumb.className =
        "attachment-thumb";

      thumb.textContent =
        fileIcon(file);


      const meta =
        document.createElement("div");

      meta.className =
        "attachment-meta";

      meta.innerHTML = `

        <b>
          ${escapeHtml(file.name)}
        </b>

        <small>
          ${formatBytes(file.size)}
        </small>
      `;


      const remove =
        document.createElement(
          "button"
        );

      remove.className =
        "remove-attachment";

      remove.type =
        "button";

      remove.textContent =
        "×";


      remove.addEventListener(
        "click",
        () => {

          selectedFiles.splice(
            index,
            1
          );

          renderAttachments();
        }
      );


      card.append(
        thumb,
        meta,
        remove
      );


      attachmentStrip
        .appendChild(card);
    }
  );
}


/* =========================================================
   ADD FILES
========================================================= */

function addFiles(fileList) {

  const incoming =
    [...fileList];


  for (const file of incoming) {

    /*
     * IMAGE UPLOAD DISABLED
     */

    if (
      file.type.startsWith("image/")
    ) {

      showToast(
        "Image upload is disabled in this build.",
        "error"
      );

      continue;
    }


    /*
     * Unsupported file
     */

    if (
      !isSupportedFile(file)
    ) {

      showToast(
        `${file.name}: unsupported file type.`,
        "error"
      );

      continue;
    }


    /*
     * File size validation
     */

    if (
      file.size > MAX_FILE_SIZE
    ) {

      showToast(
        `${file.name} is larger than 25 MB.`,
        "error"
      );

      continue;
    }


    /*
     * Duplicate detection
     */

    const duplicate =
      selectedFiles.some(
        (existing) =>
          existing.name ===
            file.name &&
          existing.size ===
            file.size
      );


    if (!duplicate) {

      selectedFiles.push(file);

    }
  }


  /*
   * Attachment count limit
   */

  if (
    selectedFiles.length >
    MAX_ATTACHMENTS
  ) {

    selectedFiles =
      selectedFiles.slice(
        0,
        MAX_ATTACHMENTS
      );


    showToast(
      `Maximum ${MAX_ATTACHMENTS} attachments per message.`,
      "error"
    );
  }


  renderAttachments();
}


/* =========================================================
   API RESPONSE HANDLING
========================================================= */

async function readJsonResponse(
  response
) {

  const raw =
    await response.text();


  let data = {};


  if (raw) {

    try {

      data =
        JSON.parse(raw);

    } catch {

      data = {
        detail: raw
      };

    }
  }


  if (!response.ok) {

    throw new Error(
      data.detail ||
      data.error ||
      `HTTP ${response.status}`
    );
  }


  return data;
}


/* =========================================================
   GENERIC ATTACHMENT UPLOAD
========================================================= */

async function uploadGeneric(
  file
) {

  const form =
    new FormData();

  form.append(
    "file",
    file
  );


  const response =
    await fetch(
      "/api/attachments/upload",
      {
        method: "POST",
        body: form,
      }
    );


  return readJsonResponse(
    response
  );
}


/* =========================================================
   AUDIO TRANSCRIPTION
========================================================= */

async function transcribeAudio(
  file
) {

  const form =
    new FormData();

  form.append(
    "file",
    file
  );


  const response =
    await fetch(
      "/api/speech/transcribe",
      {
        method: "POST",
        body: form,
      }
    );


  return readJsonResponse(
    response
  );
}


/* =========================================================
   ATTACHMENT PROCESSING
========================================================= */

async function processAttachments(
  files
) {

  const context = [];

  let shouldUseRag =
    ragEnabled;


  for (const file of files) {

    setMiniStatus(
      `UPLOADING ${file.name.slice(
        0,
        14
      )}`,
      "thinking"
    );


    /*
     * AUDIO
     */

    if (
      file.type.startsWith(
        "audio/"
      )
    ) {

      const result =
        await transcribeAudio(
          file
        );


      context.push(
        `Audio ${file.name} transcript:\n${result.text}`
      );


      continue;
    }


    /*
     * DOCUMENT / CODE / VIDEO
     */

    const result =
      await uploadGeneric(
        file
      );


    /*
     * Documents ingested into RAG
     */

    if (
      result.document_id
    ) {

      shouldUseRag =
        true;
    }


    /*
     * Video is stored only.
     */

    if (
      result.kind === "video"
    ) {

      context.push(

        `Video attachment stored: ${result.filename} ` +
        `(${formatBytes(result.size)}). ` +
        `Semantic video-frame analysis is not enabled in this build.`

      );

    }

    else if (
      !result.document_id
    ) {

      context.push(

        `Attachment stored: ${result.filename} ` +
        `(${result.kind}, ${formatBytes(result.size)}).`

      );

    }
  }


  return {

    context,

    shouldUseRag

  };
}


/* =========================================================
   SEND CHAT MESSAGE
========================================================= */

async function sendMessage() {

  if (busy) {
    return;
  }


  const text =
    promptInput.value.trim();


  if (
    !text &&
    selectedFiles.length === 0
  ) {
    return;
  }


  const files =
    [...selectedFiles];


  addMessage(
    "user",
    text ||
      "Analyze the attached content.",
    files
  );


  promptInput.value =
    "";

  selectedFiles =
    [];


  renderAttachments();

  resizePrompt();

  setBusy(true);

  setMiniStatus(
    "THINKING",
    "thinking"
  );


  try {

    /*
     * Process files first
     */

    const attachmentResult =
      await processAttachments(
        files
      );


    /*
     * Add attachment context
     */

    const messageWithContext = [

      text ||
        "Analyze the attached content.",

      attachmentResult
        .context
        .length

        ? `\nATTACHMENT CONTEXT:\n${attachmentResult.context.join(
            "\n\n"
          )}`

        : ""

    ]
      .join("")
      .trim();


    /*
     * Select endpoint
     */

    const endpoint =
      agentEnabled
        ? "/api/agent/run"
        : "/api/chat";


    const payload = {

      message:
        messageWithContext,

      session_id:
        sessionId,

      use_rag:
        attachmentResult
          .shouldUseRag

    };


    /*
     * Send request
     */

    const response =
      await fetch(
        endpoint,
        {

          method:
            "POST",

          headers: {

            "Content-Type":
              "application/json"

          },

          body:
            JSON.stringify(
              payload
            )

        }
      );


    const data =
      await readJsonResponse(
        response
      );


    const answer =

      data.answer ||

      data.message ||

      "I received an empty response.";


    addMessage(
      "assistant",
      answer
    );


    speak(answer);

  }

  catch (error) {

    console.error(
      error
    );


    const message =

      error instanceof Error

        ? error.message

        : "Unknown request error";


    addMessage(

      "assistant",

      `Request failed: ${message}`

    );


    setMiniStatus(
      "ERROR",
      "error"
    );

  }

  finally {

    setBusy(false);


    if (
      !window
        .speechSynthesis
        ?.speaking
    ) {

      setMiniStatus(
        "READY",
        "idle"
      );

    }
  }
}


/* =========================================================
   TEXT TO SPEECH
========================================================= */

function chooseVoice() {

  const voices =
    window
      .speechSynthesis
      ?.getVoices?.() ||
    [];


  const preferred = [

    "Microsoft David",

    "Microsoft Mark",

    "Microsoft Guy",

    "Google UK English Male"

  ];


  for (
    const name of preferred
  ) {

    const voice =
      voices.find(
        (item) =>
          item.name
            .toLowerCase()
            .includes(
              name.toLowerCase()
            )
      );


    if (voice) {

      return voice;

    }
  }


  return (

    voices.find(
      (voice) =>
        voice.lang
          .toLowerCase()
          .startsWith("en")
    )

    ||

    voices[0]

    ||

    null

  );
}


function speak(text) {

  if (
    !voiceEnabled ||
    !(
      "speechSynthesis"
      in window
    )
  ) {

    return;

  }


  window
    .speechSynthesis
    .cancel();


  const cleanText =
    text.replace(
      /```[\s\S]*?```/g,
      "Code block omitted from speech."
    );


  const utterance =
    new SpeechSynthesisUtterance(
      cleanText
    );


  const voice =
    chooseVoice();


  if (voice) {

    utterance.voice =
      voice;

  }


  utterance.rate =
    1.02;

  utterance.pitch =
    0.9;


  utterance.onstart =
    () => {

      setMiniStatus(
        "SPEAKING",
        "thinking"
      );

    };


  utterance.onend =
    () => {

      setMiniStatus(
        "READY",
        "idle"
      );

    };


  utterance.onerror =
    () => {

      setMiniStatus(
        "VOICE ERROR",
        "error"
      );

    };


  window
    .speechSynthesis
    .speak(
      utterance
    );
}


/* =========================================================
   SPEECH RECOGNITION
========================================================= */

function initializeSpeechRecognition() {

  const Recognition =

    window.SpeechRecognition

    ||

    window.webkitSpeechRecognition;


  if (!Recognition) {

    return;

  }


  recognition =
    new Recognition();


  recognition.continuous =
    false;

  recognition.interimResults =
    true;

  recognition.lang =
    "en-IN";


  recognition.onstart =
    () => {

      isListening =
        true;


      $("#micButton")
        .classList
        .add(
          "listening"
        );


      setMiniStatus(
        "LISTENING",
        "listening"
      );

    };


  recognition.onresult =
    (event) => {

      let finalText =
        "";

      let interim =
        "";


      for (

        let i =
          event.resultIndex;

        i <
          event.results.length;

        i += 1

      ) {

        const value =
          event
            .results[i][0]
            .transcript;


        if (
          event.results[i]
            .isFinal
        ) {

          finalText +=
            value;

        }

        else {

          interim +=
            value;

        }
      }


      promptInput.value =

        finalText

        ||

        interim;


      resizePrompt();

    };


  recognition.onerror =
    (event) => {

      isListening =
        false;


      $("#micButton")
        .classList
        .remove(
          "listening"
        );


      const label =

        event.error ===
        "not-allowed"

          ? "MIC DENIED"

          : event.error ===
            "no-speech"

            ? "NO SPEECH"

            : "VOICE ERROR";


      setMiniStatus(

        label,

        event.error ===
        "no-speech"

          ? "idle"

          : "error"

      );

    };


  recognition.onend =
    () => {

      isListening =
        false;


      $("#micButton")
        .classList
        .remove(
          "listening"
        );


      if (!busy) {

        setMiniStatus(
          "READY",
          "idle"
        );

      }
    };
}


/* =========================================================
   MICROPHONE TOGGLE
========================================================= */

function toggleListening() {

  if (!recognition) {

    initializeSpeechRecognition();

  }


  if (!recognition) {

    showToast(

      "Speech recognition is not supported by this browser.",

      "error"

    );

    return;

  }


  if (isListening) {

    recognition.stop();

  }

  else {

    window
      .speechSynthesis
      ?.cancel();


    try {

      recognition.start();

    }

    catch (error) {

      console.error(
        error
      );

    }
  }
}


/* =========================================================
   TEXTAREA RESIZE
========================================================= */

function resizePrompt() {

  promptInput.style.height =
    "auto";


  promptInput.style.height =

    `${Math.min(

      promptInput.scrollHeight,

      180

    )}px`;

}


/* =========================================================
   PANEL NAVIGATION
========================================================= */

function switchPanel(
  panelId
) {

  $$(".panel")
    .forEach(
      (panel) => {

        panel
          .classList
          .toggle(

            "visible",

            panel.id ===
              panelId

          );

      }
    );


  $$(".nav-item")
    .forEach(
      (item) => {

        item
          .classList
          .toggle(

            "active",

            item.dataset.panel ===
              panelId

          );

      }
    );


  $("#sidebar")
    .classList
    .remove("open");
}


/* =========================================================
   RESET CHAT
========================================================= */

function resetChat() {

  sessionId =
    crypto.randomUUID();


  $$("#chat > .message")
    .forEach(
      (message) =>
        message.remove()
    );


  $("#welcome")
    ?.classList
    .remove(
      "hidden"
    );


  $("#session")
    .textContent =

      sessionId.slice(
        0,
        8
      );


  selectedFiles =
    [];


  renderAttachments();


  promptInput.value =
    "";


  promptInput.focus();
}


/* =========================================================
   HEALTH CHECK
========================================================= */

async function refreshHealth() {

  try {

    const response =
      await fetch(
        "/health"
      );


    const data =
      await readJsonResponse(
        response
      );


    $("#health")
      .textContent =
        "System online";


    $("#provider")
      .textContent =

        data.provider

        ||

        "connected";


    $("#modelLabel")
      .textContent =

        `${String(

          data.provider

          ||

          "AUTO"

        ).toUpperCase()} ROUTING`;


    $("#statusDot")
      .classList
      .remove(
        "error"
      );

  }

  catch {

    $("#health")
      .textContent =
        "Backend offline";


    $("#provider")
      .textContent =
        "disconnected";


    $("#statusDot")
      .classList
      .add(
        "error"
      );

  }
}


/* =========================================================
   KNOWLEDGE INGESTION
========================================================= */

async function ingestKnowledge() {

  const title =
    $("#docTitle")
      .value
      .trim();


  const text =
    $("#docText")
      .value
      .trim();


  if (
    !title ||
    !text
  ) {

    return showToast(

      "Add both a title and content.",

      "error"

    );
  }


  try {

    const response =
      await fetch(

        "/api/documents/ingest",

        {

          method:
            "POST",

          headers: {

            "Content-Type":
              "application/json"

          },

          body:
            JSON.stringify({

              title,

              text,

              source:
                "ui"

            })

        }

      );


    const data =
      await readJsonResponse(
        response
      );


    const box =
      $("#ingestResult");


    box.hidden =
      false;


    box.textContent =
      JSON.stringify(

        data,

        null,

        2

      );


    showToast(
      "Knowledge ingested successfully."
    );

  }

  catch (error) {

    showToast(

      error.message,

      "error"

    );

  }
}


/* =========================================================
   MULTI-AGENT REVIEW
========================================================= */

async function runAgentReview() {

  const goal =
    $("#agentGoal")
      .value
      .trim();


  if (!goal) {

    return showToast(

      "Describe a goal first.",

      "error"

    );

  }


  const box =
    $("#agentResult");


  box.hidden =
    false;


  box.textContent =
    "Running review workflow…";


  try {

    const response =
      await fetch(

        "/api/agents/review",

        {

          method:
            "POST",

          headers: {

            "Content-Type":
              "application/json"

          },

          body:
            JSON.stringify({

              goal,

              session_id:
                sessionId

            })

        }

      );


    const data =
      await readJsonResponse(
        response
      );


    box.textContent =
      JSON.stringify(

        data,

        null,

        2

      );

  }

  catch (error) {

    box.textContent =
      error.message;

  }
}


/* =========================================================
   INITIAL UI STATE
========================================================= */

$("#session")
  .textContent =
    sessionId.slice(
      0,
      8
    );


/* =========================================================
   BUTTON EVENTS
========================================================= */

$("#send")
  .addEventListener(
    "click",
    sendMessage
  );


$("#attachButton")
  .addEventListener(
    "click",
    () => {

      fileInput.click();

    }
  );


fileInput
  .addEventListener(
    "change",
    () => {

      addFiles(
        fileInput.files
      );

      fileInput.value =
        "";

    }
  );


$("#micButton")
  .addEventListener(
    "click",
    toggleListening
  );


$("#speakerButton")
  .addEventListener(
    "click",
    (event) => {

      voiceEnabled =
        !voiceEnabled;


      event
        .currentTarget
        .classList
        .toggle(

          "active",

          voiceEnabled

        );


      event
        .currentTarget
        .textContent =

          voiceEnabled

            ? "🔊"

            : "🔇";


      if (!voiceEnabled) {

        window
          .speechSynthesis
          ?.cancel();

      }

    }
  );


$("#ragToggle")
  .addEventListener(
    "click",
    (event) => {

      ragEnabled =
        !ragEnabled;


      event
        .currentTarget
        .classList
        .toggle(

          "active",

          ragEnabled

        );

    }
  );


$("#agentToggle")
  .addEventListener(
    "click",
    (event) => {

      agentEnabled =
        !agentEnabled;


      event
        .currentTarget
        .classList
        .toggle(

          "active",

          agentEnabled

        );

    }
  );


$("#newChat")
  .addEventListener(
    "click",
    () => {

      switchPanel(
        "chatPanel"
      );

      resetChat();

    }
  );


$("#clearChat")
  .addEventListener(
    "click",
    resetChat
  );


$("#openSidebar")
  .addEventListener(
    "click",
    () => {

      $("#sidebar")
        .classList
        .add("open");

    }
  );


$("#closeSidebar")
  .addEventListener(
    "click",
    () => {

      $("#sidebar")
        .classList
        .remove("open");

    }
  );


$("#ingestButton")
  .addEventListener(
    "click",
    ingestKnowledge
  );


$("#agentRunButton")
  .addEventListener(
    "click",
    runAgentReview
  );


$("#knowledgeUpload")
  .addEventListener(
    "click",
    () => {

      switchPanel(
        "chatPanel"
      );

      fileInput.click();

    }
  );


/* =========================================================
   NAVIGATION
========================================================= */

$$(".nav-item")
  .forEach(
    (item) => {

      item.addEventListener(
        "click",
        () => {

          switchPanel(
            item.dataset.panel
          );

        }
      );

    }
  );


/* =========================================================
   STARTER PROMPTS
========================================================= */

$$(".starter")
  .forEach(
    (button) => {

      button.addEventListener(
        "click",
        () => {

          promptInput.value =

            button.dataset.prompt

            ||

            "";


          resizePrompt();

          promptInput.focus();

        }
      );

    }
  );


/* =========================================================
   PROMPT EVENTS
========================================================= */

promptInput
  .addEventListener(
    "input",
    resizePrompt
  );


promptInput
  .addEventListener(
    "keydown",
    (event) => {

      if (
        event.key ===
          "Enter"

        &&

        !event.shiftKey
      ) {

        event.preventDefault();

        sendMessage();

      }

    }
  );


/* =========================================================
   DRAG AND DROP
========================================================= */

[
  "dragenter",
  "dragover"
]
  .forEach(
    (name) => {

      dropZone
        .addEventListener(
          name,
          (event) => {

            event.preventDefault();

            dropZone
              .classList
              .add(
                "dragging"
              );

          }
        );

    }
  );


[
  "dragleave",
  "drop"
]
  .forEach(
    (name) => {

      dropZone
        .addEventListener(
          name,
          (event) => {

            event.preventDefault();

            dropZone
              .classList
              .remove(
                "dragging"
              );

          }
        );

    }
  );


dropZone
  .addEventListener(
    "drop",
    (event) => {

      addFiles(
        event
          .dataTransfer
          .files
      );

    }
  );


/* =========================================================
   CLIPBOARD FILE PASTE
========================================================= */

window
  .addEventListener(
    "paste",
    (event) => {

      const files = [

        ...(
          event
            .clipboardData
            ?.files

          ||

          []
        )

      ];


      if (
        files.length
      ) {

        addFiles(
          files
        );

      }

    }
  );


/* =========================================================
   KEYBOARD SHORTCUT
========================================================= */

window
  .addEventListener(
    "keydown",
    (event) => {

      if (

        (
          event.ctrlKey

          ||

          event.metaKey
        )

        &&

        event.key
          .toLowerCase() ===
          "k"

      ) {

        event.preventDefault();

        resetChat();

      }

    }
  );


/* =========================================================
   STARTUP
========================================================= */

initializeSpeechRecognition();

refreshHealth();

setInterval(
  refreshHealth,
  30000
);

resizePrompt();