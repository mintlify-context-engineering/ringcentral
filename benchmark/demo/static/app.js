const panes = {
  raw: {
    status: document.querySelector("#raw-status"),
    output: document.querySelector("#raw-output"),
    tools: document.querySelector("#raw-tools"),
    metrics: document.querySelector("#raw-metrics"),
  },
  mcp: {
    status: document.querySelector("#mcp-status"),
    output: document.querySelector("#mcp-output"),
    tools: document.querySelector("#mcp-tools"),
    metrics: document.querySelector("#mcp-metrics"),
  },
};

const promptInput = document.querySelector("#prompt");
const modelInput = document.querySelector("#model");
const runButton = document.querySelector("#run");
const stopButton = document.querySelector("#stop");
let controllers = [];

function setMetric(mode, key, value) {
  const target = panes[mode].metrics.querySelector(`[data-metric="${key}"]`);
  if (target) target.textContent = value;
}

function formatNumber(value) {
  return new Intl.NumberFormat().format(Math.round(Number(value) || 0));
}

function formatCost(value) {
  return `$${(Number(value) || 0).toFixed(4)}`;
}

function setStatus(mode, text, state = "") {
  const node = panes[mode].status;
  node.textContent = text;
  node.className = `status ${state}`.trim();
}

function resetPane(mode) {
  panes[mode].output.textContent = "";
  panes[mode].tools.textContent = "";
  setStatus(mode, "Queued", "running");
  for (const key of ["prompt", "completion", "total", "tools", "bytes"]) {
    setMetric(mode, key, "0");
  }
  setMetric(mode, "cost", "$0.0000");
}

function appendToolCall(mode, data) {
  const item = document.createElement("li");
  item.className = "tool-item";
  item.dataset.toolName = data.name;
  item.innerHTML = `
    <div class="tool-name"><strong></strong><span></span></div>
    <pre class="tool-args"></pre>
  `;
  item.querySelector("strong").textContent = data.name || "tool";
  item.querySelector("span").textContent = `round ${data.round || 1}`;
  item.querySelector(".tool-args").textContent = JSON.stringify(data.arguments || {}, null, 2);
  panes[mode].tools.appendChild(item);
  panes[mode].tools.scrollTop = panes[mode].tools.scrollHeight;
}

function appendToolResult(mode, data) {
  const items = [...panes[mode].tools.querySelectorAll(".tool-item")];
  const item = items.reverse().find((node) => node.dataset.toolName === data.name) || items[items.length - 1];
  if (!item) return;
  let preview = item.querySelector(".tool-preview");
  if (!preview) {
    preview = document.createElement("pre");
    preview.className = "tool-preview";
    item.appendChild(preview);
  }
  preview.textContent = `${formatNumber(data.bytes)} bytes\n\n${data.preview || ""}`;
  panes[mode].tools.scrollTop = panes[mode].tools.scrollHeight;
}

function updateUsage(mode, data) {
  setMetric(mode, "prompt", formatNumber(data.prompt_tokens));
  setMetric(mode, "completion", formatNumber(data.completion_tokens));
  setMetric(mode, "total", formatNumber(data.total_tokens));
  setMetric(mode, "tools", formatNumber(data.tool_calls));
  setMetric(mode, "bytes", formatNumber(data.tool_result_bytes));
  setMetric(mode, "cost", formatCost(data.cost));
}

function parseSseBlock(block) {
  const lines = block.split("\n");
  let event = "message";
  const dataLines = [];
  for (const line of lines) {
    if (line.startsWith("event:")) {
      event = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trimStart());
    }
  }
  return { event, data: JSON.parse(dataLines.join("\n") || "{}") };
}

function handleEvent(mode, event, data) {
  if (event === "status") {
    setStatus(mode, data.message || "Running", "running");
  } else if (event === "ready") {
    setStatus(mode, "Running", "running");
  } else if (event === "content") {
    panes[mode].output.textContent += data.text || "";
    panes[mode].output.scrollTop = panes[mode].output.scrollHeight;
  } else if (event === "tool_call") {
    appendToolCall(mode, data);
  } else if (event === "tool_result") {
    appendToolResult(mode, data);
  } else if (event === "usage") {
    updateUsage(mode, data);
  } else if (event === "done") {
    updateUsage(mode, data);
    setStatus(mode, `${Number(data.elapsed_s || 0).toFixed(1)}s`, "");
  } else if (event === "error") {
    setStatus(mode, "Error", "error");
    panes[mode].output.textContent += `\n\n${data.message || "Run failed"}`;
  }
}

async function streamRun(mode, prompt, model, signal) {
  const response = await fetch("/api/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mode, prompt, model }),
    signal,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: response.statusText }));
    throw new Error(error.error || response.statusText);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() || "";
    for (const block of blocks) {
      if (!block.trim()) continue;
      const parsed = parseSseBlock(block);
      handleEvent(mode, parsed.event, parsed.data);
    }
  }
}

async function runBoth() {
  const prompt = promptInput.value.trim();
  const model = modelInput.value.trim();
  if (!prompt) {
    promptInput.focus();
    return;
  }

  controllers.forEach((controller) => controller.abort());
  controllers = [new AbortController(), new AbortController()];
  resetPane("raw");
  resetPane("mcp");
  runButton.disabled = true;
  stopButton.disabled = false;

  const tasks = [
    streamRun("raw", prompt, model, controllers[0].signal).catch((error) => {
      if (error.name !== "AbortError") handleEvent("raw", "error", { message: error.message });
    }),
    streamRun("mcp", prompt, model, controllers[1].signal).catch((error) => {
      if (error.name !== "AbortError") handleEvent("mcp", "error", { message: error.message });
    }),
  ];

  await Promise.allSettled(tasks);
  runButton.disabled = false;
  stopButton.disabled = true;
}

runButton.addEventListener("click", runBoth);
stopButton.addEventListener("click", () => {
  controllers.forEach((controller) => controller.abort());
  setStatus("raw", "Stopped", "");
  setStatus("mcp", "Stopped", "");
  runButton.disabled = false;
  stopButton.disabled = true;
});

promptInput.addEventListener("keydown", (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
    runBoth();
  }
});

const config = await fetch("/api/config").then((response) => response.json());
modelInput.value = config.default_model || "~openai/gpt-latest";
if (!config.has_openrouter_key) {
  setStatus("raw", "No key", "error");
  setStatus("mcp", "No key", "error");
}
