import { useCallback, useEffect, useRef, useState } from "react";
import { Box, Button, Chip, Stack, Typography } from "@mui/material";
import {
  createSessionWebSocket,
  sendInterrupt,
  sendMessage,
} from "../api";
import { terminalColors } from "../theme";
import type {
  ActivityMode,
  EnvMode,
  I18nStrings,
  PromptSet,
  ServerEvent,
  StepRecord,
  TerminalLine,
  TodoItem,
  UpdateEvent,
} from "../types";
import { InputBar } from "./InputBar";
import { StreamingLine } from "./StreamingLine";
import { TaskBackgroundEditor } from "./TaskBackgroundEditor";
import { Timeline } from "./Timeline";
import { Todos } from "./Todos";

interface TerminalProps {
  sessionId: string;
  envMode: EnvMode;
  promptSet: PromptSet;
  onExit: () => void;
}

let lineCounter = 0;
function nextLineId(prefix: string): string {
  lineCounter += 1;
  return `${prefix}-${lineCounter}`;
}

export function Terminal({ sessionId, envMode, promptSet, onExit }: TerminalProps) {
  const [lines, setLines] = useState<TerminalLine[]>([]);
  const [steps, setSteps] = useState<Record<string, StepRecord>>({});
  const [todos, setTodos] = useState<TodoItem[]>([]);
  const [todosLineId, setTodosLineId] = useState<string | null>(null);
  const [streamingText, setStreamingText] = useState("");
  const [activityMode, setActivityMode] = useState<ActivityMode>("idle");
  const [i18n, setI18n] = useState<I18nStrings | null>(null);
  const [input, setInput] = useState("");
  const [connected, setConnected] = useState(false);
  const [busy, setBusy] = useState(false);
  const [frameIndex, setFrameIndex] = useState(0);
  const [editorOpen, setEditorOpen] = useState(false);
  const lastWorkspaceSummaryRef = useRef<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const stepLineIdsRef = useRef<Record<string, string>>({});

  const appendLine = useCallback((line: TerminalLine) => {
    setLines((prev) => [...prev, line]);
  }, []);

  const applyUpdate = useCallback(
    (event: UpdateEvent) => {
      if (Object.keys(event.steps).length) {
        setSteps((prev) => ({ ...prev, ...event.steps }));
      }

      for (const entry of event.timeline) {
        if (entry.kind === "step" && entry.step_id) {
          const step = event.steps[entry.step_id];
          if (step) {
            const existingLineId = stepLineIdsRef.current[step.step_id];
            if (existingLineId) {
              setLines((prev) =>
                prev.map((line) =>
                  line.id === existingLineId ? { ...line, step } : line,
                ),
              );
            } else {
              const lineId = nextLineId("step");
              stepLineIdsRef.current[step.step_id] = lineId;
              appendLine({ id: lineId, kind: "step", step });
            }
            continue;
          }
        }
        appendLine({
          id: nextLineId(entry.kind),
          kind: entry.kind,
          text: entry.text,
        });
      }

      if (event.todos.length) {
        setTodos(event.todos);
        setTodosLineId((prev) => prev ?? nextLineId("todos"));
      }

      if (event.streaming_assistant !== null && event.streaming_assistant !== undefined) {
        setStreamingText(event.streaming_assistant);
      }

      if (event.activity_mode) {
        setActivityMode(event.activity_mode);
        setBusy(event.activity_mode !== "idle");
      } else if (event.activity_mode === null) {
        // keep current
      }

      if (event.workspace_summary) {
        const prefix = event.workspace_prefix ?? "workspace";
        const summary = `${prefix} · ${event.workspace_summary}`;
        if (summary !== lastWorkspaceSummaryRef.current) {
          lastWorkspaceSummaryRef.current = summary;
          appendLine({ id: nextLineId("system"), kind: "system", text: summary });
        }
      }
    },
    [appendLine],
  );

  const handleServerEvent = useCallback(
    (event: ServerEvent) => {
      if (event.type === "banner") {
        setI18n(event.i18n);
        lastWorkspaceSummaryRef.current = event.workspace_summary;
        setLines([
          {
            id: nextLineId("banner"),
            kind: "banner",
            text: `${event.title}  workspace=${event.workspace_root}`,
          },
          {
            id: nextLineId("banner"),
            kind: "system",
            text: event.workspace_summary,
          },
          {
            id: nextLineId("banner"),
            kind: "system",
            text: event.i18n.banner_hint,
          },
        ]);
        return;
      }

      if (event.type === "step_refresh") {
        setSteps((prev) => ({ ...prev, [event.step.step_id]: event.step }));
        const lineId = stepLineIdsRef.current[event.step.step_id];
        if (lineId) {
          setLines((prev) =>
            prev.map((line) =>
              line.id === lineId ? { ...line, step: event.step } : line,
            ),
          );
        }
        return;
      }

      if (event.type === "update") {
        if (event.activity_mode === "idle") {
          setBusy(false);
          setStreamingText("");
          setActivityMode("idle");
        }
        applyUpdate(event);
      }
    },
    [applyUpdate],
  );

  useEffect(() => {
    lineCounter = 0;
    stepLineIdsRef.current = {};
    setLines([]);
    setSteps({});
    setTodos([]);
    setTodosLineId(null);
    setStreamingText("");
    setActivityMode("idle");
    setBusy(false);
    lastWorkspaceSummaryRef.current = null;

    const ws = createSessionWebSocket(
      sessionId,
      handleServerEvent,
      () => setConnected(false),
      () => setConnected(false),
    );
    wsRef.current = ws;
    ws.onopen = () => setConnected(true);

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [sessionId, handleServerEvent]);

  useEffect(() => {
    if (!busy && activityMode === "idle") return;
    const timer = window.setInterval(() => {
      setFrameIndex((prev) => prev + 1);
    }, 120);
    return () => window.clearInterval(timer);
  }, [busy, activityMode]);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [lines, streamingText, todos, busy, activityMode]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && wsRef.current?.readyState === WebSocket.OPEN) {
        sendInterrupt(wsRef.current);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const handleSubmit = () => {
    const text = input.trim();
    if (!text || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      return;
    }
    if (["exit", "quit", "/exit", "/quit"].includes(text.toLowerCase())) {
      sendMessage(wsRef.current, text);
      setInput("");
      window.setTimeout(onExit, 300);
      return;
    }
    setBusy(true);
    sendMessage(wsRef.current, text);
    setInput("");
  };

  const activityLabels = i18n?.activity_labels ?? {
    thinking: "Agent 思考中",
    tool: "执行工具",
    streaming: "生成回复",
  };

  return (
    <Box
      sx={{
        flex: 1,
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        minWidth: 0,
      }}
    >
      <Box
        sx={{
          px: 2,
          py: 1,
          borderBottom: `1px solid ${terminalColors.border}`,
          bgcolor: terminalColors.panel,
        }}
      >
        <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
          <Typography variant="caption" sx={{ color: terminalColors.gray }}>
            {sessionId}
          </Typography>
          <Chip size="small" label={envMode} sx={{ height: 20, fontSize: "0.7rem" }} />
          <Chip size="small" label={promptSet} sx={{ height: 20, fontSize: "0.7rem" }} />
          <Button size="small" variant="outlined" onClick={() => setEditorOpen(true)}>
            编辑 task_background
          </Button>
        </Stack>
      </Box>

      <Box
        ref={scrollRef}
        sx={{
          flex: 1,
          overflow: "auto",
          p: 2,
          fontFamily: "inherit",
        }}
      >
        {lines.map((line) => {
          if (line.kind === "banner" || line.kind === "system" || line.kind === "user" || line.kind === "assistant" || line.kind === "error") {
            return (
              <Timeline
                key={line.id}
                entry={{
                  kind: line.kind === "banner" ? "system" : line.kind,
                  text: line.text ?? "",
                  step_id: null,
                }}
              />
            );
          }
          if (line.kind === "step" && line.step) {
            return <Timeline key={line.id} entry={{ kind: "step", text: "", step_id: line.step.step_id }} step={line.step} />;
          }
          return null;
        })}

        {todos.length > 0 && todosLineId && (
          <Todos title={i18n?.plan_title ?? "Plan"} items={todos} />
        )}

        {(streamingText || (busy && activityMode !== "idle")) && (
          <StreamingLine
            text={streamingText}
            activityMode={activityMode ?? "thinking"}
            activityLabels={activityLabels}
            frameIndex={frameIndex}
          />
        )}

        {!connected && (
          <Typography sx={{ color: terminalColors.yellow, mt: 1 }}>
            连接中…
          </Typography>
        )}
      </Box>

      <InputBar
        value={input}
        onChange={setInput}
        onSubmit={handleSubmit}
        disabled={!connected}
      />
      <TaskBackgroundEditor
        sessionId={sessionId}
        open={editorOpen}
        onClose={() => setEditorOpen(false)}
      />
    </Box>
  );
}
