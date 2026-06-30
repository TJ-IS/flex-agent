import {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
} from "react";
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogContent,
  DialogTitle,
  Tab,
  Tabs,
  TextField,
  Typography,
} from "@mui/material";
import {
  downloadFileUrl,
  getTextFile,
  saveTaskBackground,
  uploadFile,
  type WorkspaceTextPath,
} from "../api";
import { monoFont, terminalColors } from "../theme";

interface WorkspaceEditorProps {
  sessionId: string;
  open: boolean;
  onClose: () => void;
}

type SaveState = "idle" | "saving" | "saved" | "error";

export type TabSaveStatus = {
  saveState: SaveState;
  dirty: boolean;
};

export interface EditableFileTabHandle {
  flush: () => Promise<void>;
}

const AUTOSAVE_DELAY_MS = 800;

interface EditableFileTabProps {
  sessionId: string;
  open: boolean;
  isActive: boolean;
  loadPath: WorkspaceTextPath;
  save: (sessionId: string, content: string) => Promise<void>;
  downloadUrl?: string;
  savedLabel?: string;
  onStatusChange: (status: TabSaveStatus) => void;
}

const EditableFileTab = forwardRef<EditableFileTabHandle, EditableFileTabProps>(
  function EditableFileTab(
    {
      sessionId,
      open,
      isActive,
      loadPath,
      save,
      downloadUrl,
      savedLabel = "已保存 · agent 已重载",
      onStatusChange,
    },
    ref,
  ) {
    const [content, setContent] = useState("");
    const [loading, setLoading] = useState(false);
    const [saveState, setSaveState] = useState<SaveState>("idle");
    const [error, setError] = useState<string | null>(null);

    const contentRef = useRef("");
    const lastSavedRef = useRef("");
    const dirtyRef = useRef(false);
    const saveTimerRef = useRef<number | null>(null);
    const inFlightRef = useRef(false);
    const loadedRef = useRef(false);

    const reportStatus = (state: SaveState) => {
      onStatusChange({ saveState: state, dirty: dirtyRef.current });
    };

    useEffect(() => {
      contentRef.current = content;
    }, [content]);

    useEffect(() => {
      if (!open || !isActive) return;
      if (loadedRef.current) return;
      setLoading(true);
      setError(null);
      setSaveState("idle");
      void getTextFile(sessionId, loadPath)
        .then((text) => {
          setContent(text);
          contentRef.current = text;
          lastSavedRef.current = text;
          dirtyRef.current = false;
          loadedRef.current = true;
          reportStatus("idle");
        })
        .catch((err: unknown) => {
          setError(err instanceof Error ? err.message : "加载失败");
        })
        .finally(() => setLoading(false));
    }, [open, isActive, sessionId, loadPath]);

    useEffect(() => {
      if (open) return;
      loadedRef.current = false;
      if (saveTimerRef.current !== null) {
        window.clearTimeout(saveTimerRef.current);
        saveTimerRef.current = null;
      }
      setSaveState("idle");
      dirtyRef.current = false;
    }, [open]);

    const runSave = async (value: string) => {
      if (inFlightRef.current) return;
      if (value === lastSavedRef.current) {
        dirtyRef.current = false;
        setSaveState("idle");
        reportStatus("idle");
        return;
      }
      inFlightRef.current = true;
      setSaveState("saving");
      reportStatus("saving");
      try {
        await save(sessionId, value);
        lastSavedRef.current = value;
        dirtyRef.current = false;
        setSaveState("saved");
        reportStatus("saved");
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "保存失败");
        setSaveState("error");
        reportStatus("error");
      } finally {
        inFlightRef.current = false;
      }
    };

    const flush = async () => {
      if (saveTimerRef.current !== null) {
        window.clearTimeout(saveTimerRef.current);
        saveTimerRef.current = null;
      }
      const value = contentRef.current;
      if (dirtyRef.current && value !== lastSavedRef.current) {
        await runSave(value);
      }
    };

    useImperativeHandle(ref, () => ({ flush }), [sessionId, save]);

    useEffect(() => {
      if (isActive) return;
      void flush();
    }, [isActive]);

    const scheduleSave = (value: string) => {
      if (value === lastSavedRef.current) {
        dirtyRef.current = false;
        if (saveTimerRef.current !== null) {
          window.clearTimeout(saveTimerRef.current);
          saveTimerRef.current = null;
        }
        setSaveState("idle");
        reportStatus("idle");
        return;
      }
      dirtyRef.current = true;
      setSaveState("idle");
      reportStatus("idle");
      if (saveTimerRef.current !== null) {
        window.clearTimeout(saveTimerRef.current);
      }
      saveTimerRef.current = window.setTimeout(() => {
        saveTimerRef.current = null;
        void runSave(value);
      }, AUTOSAVE_DELAY_MS);
    };

    if (!isActive) return null;

    return (
      <Box>
        {downloadUrl && (
          <Button
            size="small"
            variant="outlined"
            href={downloadUrl}
            download
            sx={{ mb: 1.5, borderColor: terminalColors.border }}
          >
            下载
          </Button>
        )}
        {error && (
          <Alert severity="warning" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}
        <TextField
          fullWidth
          multiline
          minRows={12}
          maxRows={24}
          value={content}
          disabled={loading}
          onChange={(event) => {
            const next = event.target.value;
            setContent(next);
            contentRef.current = next;
            scheduleSave(next);
          }}
          placeholder={loading ? "加载中…" : ""}
          InputProps={{
            sx: {
              fontFamily: monoFont,
              fontSize: "0.85rem",
              color: terminalColors.text,
            },
          }}
        />
        <Typography
          sx={{
            mt: 1,
            fontSize: "0.72rem",
            color: terminalColors.gray,
            opacity: 0.7,
          }}
        >
          {savedLabel}
        </Typography>
      </Box>
    );
  },
);

const TABS = [
  {
    label: "task_background.md",
    loadPath: "prompts/task_background.md" as const,
    save: saveTaskBackground,
    savedLabel: "已保存 · agent 已重载，对话记忆会被重置",
  },
  {
    label: "corpus.jsonl",
    loadPath: "files/corpus.jsonl" as const,
    save: async (sessionId: string, content: string) => {
      await uploadFile(
        sessionId,
        "corpus.jsonl",
        new File([content], "corpus.jsonl", { type: "application/x-ndjson" }),
      );
    },
    downloadKind: "corpus.jsonl" as const,
    savedLabel: "已保存 · agent 已重载",
  },
  {
    label: "corpus_with_labels.jsonl",
    loadPath: "files/corpus_with_labels.jsonl" as const,
    save: async (sessionId: string, content: string) => {
      await uploadFile(
        sessionId,
        "corpus_with_labels.jsonl",
        new File([content], "corpus_with_labels.jsonl", {
          type: "application/x-ndjson",
        }),
      );
    },
    downloadKind: "corpus_with_labels.jsonl" as const,
    savedLabel: "已保存 · agent 已重载",
  },
];

export function WorkspaceEditor({ sessionId, open, onClose }: WorkspaceEditorProps) {
  const [tabIndex, setTabIndex] = useState(0);
  const [tabStatus, setTabStatus] = useState<TabSaveStatus>({
    saveState: "idle",
    dirty: false,
  });

  const tabRefs = useRef<(EditableFileTabHandle | null)[]>([]);

  const handleClose = async () => {
    await tabRefs.current[tabIndex]?.flush();
    onClose();
  };

  const handleTabChange = async (_: unknown, next: number) => {
    if (next === tabIndex) return;
    await tabRefs.current[tabIndex]?.flush();
    setTabIndex(next);
    setTabStatus({ saveState: "idle", dirty: false });
  };

  const statusLabel = (() => {
    switch (tabStatus.saveState) {
      case "saving":
        return "保存中…";
      case "saved":
        return "已保存";
      case "error":
        return "保存失败";
      default:
        return tabStatus.dirty ? "未保存" : "已同步";
    }
  })();

  const statusColor = (() => {
    switch (tabStatus.saveState) {
      case "saving":
        return terminalColors.gray;
      case "saved":
        return terminalColors.green;
      case "error":
        return terminalColors.red;
      default:
        return tabStatus.dirty ? terminalColors.yellow : terminalColors.gray;
    }
  })();

  return (
    <Dialog open={open} onClose={() => void handleClose()} fullWidth maxWidth="md">
      <DialogTitle
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          pb: 1,
        }}
      >
        <span>编辑 workspace 文件</span>
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 0.75,
            fontSize: "0.78rem",
            color: statusColor,
            fontWeight: 400,
          }}
        >
          {tabStatus.saveState === "saving" && (
            <CircularProgress size={12} sx={{ color: statusColor }} />
          )}
          <span>{statusLabel}</span>
        </Box>
      </DialogTitle>
      <DialogContent>
        <Alert severity="info" sx={{ mb: 2 }}>
          修改会自动保存（停止输入约 {AUTOSAVE_DELAY_MS}ms 后触发）。保存后 agent
          自动重载；workspace 编码状态保留。
        </Alert>
        <Tabs
          value={tabIndex}
          onChange={(_, next) => void handleTabChange(_, next)}
          sx={{ mb: 2, borderBottom: `1px solid ${terminalColors.border}` }}
        >
          {TABS.map((tab) => (
            <Tab key={tab.label} label={tab.label} sx={{ fontSize: "0.8rem", minHeight: 40 }} />
          ))}
        </Tabs>
        {TABS.map((tab, index) => (
          <EditableFileTab
            key={tab.label}
            ref={(node) => {
              tabRefs.current[index] = node;
            }}
            sessionId={sessionId}
            open={open}
            isActive={open && tabIndex === index}
            loadPath={tab.loadPath}
            save={tab.save}
            savedLabel={tab.savedLabel}
            downloadUrl={
              "downloadKind" in tab && tab.downloadKind
                ? downloadFileUrl(sessionId, tab.downloadKind)
                : undefined
            }
            onStatusChange={tabIndex === index ? setTabStatus : () => {}}
          />
        ))}
        <Typography
          sx={{
            mt: 1,
            fontSize: "0.72rem",
            color: terminalColors.gray,
            opacity: 0.7,
          }}
        >
          切换 Tab 或关闭窗口时若有未保存改动会自动保存。
        </Typography>
      </DialogContent>
    </Dialog>
  );
}
