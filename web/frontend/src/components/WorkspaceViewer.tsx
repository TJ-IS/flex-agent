import { useEffect, useState } from "react";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Dialog,
  DialogContent,
  DialogTitle,
  Divider,
  List,
  ListItem,
  ListItemText,
  Stack,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tabs,
  Typography,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import {
  getWorkspaceOverview,
  type CodingResult,
  type DimensionItem,
  type WorkspaceOverview,
} from "../api";
import { useI18n } from "../i18n/LanguageContext";
import { cardSx, fontSizes, monoFont, terminalColors } from "../theme";

interface WorkspaceViewerProps {
  sessionId: string;
  open: boolean;
  onClose: () => void;
}

const TAB_KEYS = [
  "viewer.tabOverview",
  "viewer.tabCodebook",
  "viewer.tabCoding",
  "viewer.tabCorpus",
  "viewer.tabEval",
] as const;

function statNumber(value: unknown): string {
  if (typeof value === "number") return String(value);
  if (typeof value === "string" && value.trim()) return value;
  return "—";
}

function truncate(text: string, max = 80): string {
  if (text.length <= max) return text;
  return `${text.slice(0, max)}…`;
}

function uniqueLabels(items: CodingResult["items"]): string[] {
  const seen = new Set<string>();
  const labels: string[] = [];
  for (const item of items) {
    const label = item.normalized_label?.trim();
    if (!label || seen.has(label)) continue;
    seen.add(label);
    labels.push(label);
  }
  return labels;
}

interface EvalMetrics {
  labelKey: "viewer.metricKeyword" | "viewer.metricSemantic";
  consistency?: number;
  precision?: number;
  recall?: number;
  both?: string[];
  llmOnly?: string[];
  humanOnly?: string[];
}

function extractEvalMetrics(payload: Record<string, unknown> | null): EvalMetrics[] {
  if (!payload) return [];
  const sections: EvalMetrics[] = [];
  const keys: Record<string, EvalMetrics["labelKey"]> = {
    item_level_keyword: "viewer.metricKeyword",
    item_level_semantic: "viewer.metricSemantic",
    keyword: "viewer.metricKeyword",
    semantic: "viewer.metricSemantic",
  };
  for (const key of Object.keys(keys)) {
    const section = payload[key];
    if (!section || typeof section !== "object") continue;
    const obj = section as Record<string, unknown>;
    // Open eval: { macro: { consistency, precision, recall } }
    // Axial eval: { consistency, precision, recall } directly
    const macro = obj.macro;
    const m = macro && typeof macro === "object" ? (macro as Record<string, unknown>) : obj;
    const consistency = typeof m.consistency === "number" ? m.consistency : undefined;
    const precision = typeof m.precision === "number" ? m.precision : undefined;
    const recall = typeof m.recall === "number" ? m.recall : undefined;
    const both = Array.isArray(obj.both) ? (obj.both as string[]) : undefined;
    const llmOnly = Array.isArray(obj.llm_only) ? (obj.llm_only as string[]) : undefined;
    const humanOnly = Array.isArray(obj.human_only) ? (obj.human_only as string[]) : undefined;
    if (
      consistency === undefined &&
      precision === undefined &&
      recall === undefined &&
      !both &&
      !llmOnly &&
      !humanOnly
    ) {
      continue;
    }
    sections.push({ labelKey: keys[key], consistency, precision, recall, both, llmOnly, humanOnly });
  }
  return sections;
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <Card sx={{ ...cardSx, flex: "1 1 120px", minWidth: 120 }}>
      <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
        <Typography
          sx={{
            fontSize: "1.5rem",
            fontWeight: 700,
            color: terminalColors.cyan,
            fontFamily: monoFont,
            lineHeight: 1.2,
          }}
        >
          {value}
        </Typography>
        <Typography sx={{ fontSize: fontSizes.sm, color: terminalColors.gray, mt: 0.5 }}>
          {label}
        </Typography>
      </CardContent>
    </Card>
  );
}

function OverviewTab({ data }: { data: WorkspaceOverview }) {
  const { t } = useI18n();
  const status = data.status;
  const partition = data.partition;

  return (
    <Stack spacing={2}>
      <Stack direction="row" flexWrap="wrap" useFlexGap gap={1.5}>
        <StatCard label={t("viewer.statTotal")} value={statNumber(status.texts_total)} />
        <StatCard label={t("viewer.statCoded")} value={statNumber(status.coded_count)} />
        <StatCard label={t("viewer.statQueue")} value={statNumber(status.queue_remaining)} />
        <StatCard label={t("viewer.statDimensions")} value={statNumber(status.dimensions_count)} />
        <StatCard label={t("viewer.statEvalOpen")} value={statNumber(status.eval_open_count)} />
        <StatCard label={t("viewer.statEvalAxial")} value={statNumber(status.eval_axial_count)} />
      </Stack>

      {partition && (
        <Box>
          <Typography variant="caption" sx={{ color: terminalColors.gray, display: "block", mb: 1 }}>
            {t("viewer.partition")}
          </Typography>
          <Stack spacing={1}>
            <Stack direction="row" alignItems="center" flexWrap="wrap" useFlexGap gap={0.5}>
              <Typography sx={{ fontSize: fontSizes.sm, color: terminalColors.gray, minWidth: 72 }}>
                Seed pool
              </Typography>
              {partition.codebook_text_ids.length === 0 ? (
                <Typography sx={{ fontSize: fontSizes.sm, color: terminalColors.gray }}>—</Typography>
              ) : (
                partition.codebook_text_ids.map((id) => (
                  <Chip key={`seed-${id}`} size="small" label={id} sx={{ height: 20, fontSize: fontSizes.xs }} />
                ))
              )}
            </Stack>
            <Stack direction="row" alignItems="center" flexWrap="wrap" useFlexGap gap={0.5}>
              <Typography sx={{ fontSize: fontSizes.sm, color: terminalColors.gray, minWidth: 72 }}>
                Update pool
              </Typography>
              {partition.kevin_text_ids.length === 0 ? (
                <Typography sx={{ fontSize: fontSizes.sm, color: terminalColors.gray }}>—</Typography>
              ) : (
                partition.kevin_text_ids.map((id) => (
                  <Chip key={`update-${id}`} size="small" label={id} sx={{ height: 20, fontSize: fontSizes.xs }} />
                ))
              )}
            </Stack>
          </Stack>
        </Box>
      )}

      {data.quality_warnings && Object.keys(data.quality_warnings).length > 0 && (
        <Box>
          <Typography variant="caption" sx={{ color: terminalColors.gray, display: "block", mb: 1 }}>
            {t("viewer.qualityWarnings")}
          </Typography>
          <Stack direction="row" flexWrap="wrap" useFlexGap gap={0.5}>
            {Object.entries(data.quality_warnings).map(([key, val]) => {
              if (key === "notes" || val === 0 || val === null || val === undefined) return null;
              return (
                <Chip
                  key={key}
                  size="small"
                  label={`${key}: ${String(val)}`}
                  color="warning"
                  variant="outlined"
                  sx={{ height: 22, fontSize: fontSizes.xs }}
                />
              );
            })}
          </Stack>
          {Array.isArray(data.quality_warnings.notes) && data.quality_warnings.notes.length > 0 && (
            <List dense disablePadding sx={{ mt: 1 }}>
              {(data.quality_warnings.notes as string[]).map((note, idx) => (
                <ListItem key={idx} disablePadding sx={{ py: 0.25 }}>
                  <ListItemText
                    primary={note}
                    primaryTypographyProps={{ fontSize: fontSizes.sm, color: terminalColors.yellow }}
                  />
                </ListItem>
              ))}
            </List>
          )}
        </Box>
      )}
    </Stack>
  );
}

function CodebookTab({ dimensions }: { dimensions: DimensionItem[] }) {
  const { t } = useI18n();
  if (dimensions.length === 0) {
    return (
      <Alert severity="info" variant="outlined">
        {t("viewer.codebookEmpty")}
      </Alert>
    );
  }

  return (
    <Stack spacing={1.5}>
      {dimensions.map((dim) => (
        <Card key={dim.name} sx={cardSx}>
          <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
            <Typography sx={{ fontWeight: 600, fontSize: fontSizes.lg, mb: 0.5 }}>
              {dim.name}
            </Typography>
            {dim.definition && (
              <Typography sx={{ fontSize: fontSizes.md, color: terminalColors.gray, mb: 1 }}>
                {dim.definition}
              </Typography>
            )}
            <Stack direction="row" flexWrap="wrap" useFlexGap gap={0.5}>
              {dim.items.map((item) => (
                <Chip
                  key={item}
                  size="small"
                  label={item}
                  sx={{
                    height: 22,
                    fontSize: fontSizes.sm,
                    bgcolor: "rgba(57, 197, 207, 0.1)",
                    borderColor: "rgba(57, 197, 207, 0.35)",
                  }}
                  variant="outlined"
                />
              ))}
            </Stack>
          </CardContent>
        </Card>
      ))}
    </Stack>
  );
}

function CodingTab({ coding }: { coding: CodingResult[] }) {
  const { t } = useI18n();
  if (coding.length === 0) {
    return (
      <Alert severity="info" variant="outlined">
        {t("viewer.codingEmpty")}
      </Alert>
    );
  }

  const sorted = [...coding].sort((a, b) => a.id - b.id);

  return (
    <Stack spacing={0.5}>
      {sorted.map((entry) => {
        const labels = uniqueLabels(entry.items);
        return (
          <Accordion
            key={entry.id}
            disableGutters
            sx={{
              bgcolor: terminalColors.panel,
              border: `1px solid ${terminalColors.border}`,
              "&:before": { display: "none" },
              borderRadius: "6px !important",
              mb: 0.5,
              overflow: "hidden",
              maxWidth: "100%",
            }}
          >
            <AccordionSummary
              expandIcon={<ExpandMoreIcon sx={{ fontSize: 18 }} />}
              sx={{
                "& .MuiAccordionSummary-content": {
                  minWidth: 0,
                  overflow: "hidden",
                },
              }}
            >
              <Stack direction="row" alignItems="center" spacing={1.5} sx={{ minWidth: 0, flex: 1, overflow: "hidden" }}>
                <Chip
                  size="small"
                  label={`#${entry.id}`}
                  sx={{ height: 20, fontSize: fontSizes.xs, fontFamily: monoFont, flexShrink: 0 }}
                />
                <Typography
                  sx={{
                    fontSize: fontSizes.md,
                    color: terminalColors.text,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                    flex: 1,
                    minWidth: 0,
                  }}
                >
                  {truncate(entry.content, 60)}
                </Typography>
                <Chip
                  size="small"
                  label={t("viewer.codingLabels", { count: entry.items.length })}
                  sx={{ height: 20, fontSize: fontSizes.xs, flexShrink: 0 }}
                />
              </Stack>
            </AccordionSummary>
            <AccordionDetails sx={{ pt: 0, overflow: "hidden" }}>
              <Typography
                sx={{
                  fontSize: fontSizes.sm,
                  color: terminalColors.gray,
                  mb: 1,
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-word",
                  overflowWrap: "anywhere",
                }}
              >
                {entry.content}
              </Typography>
              {labels.length > 0 && (
                <Stack direction="row" flexWrap="wrap" useFlexGap gap={0.5} sx={{ mb: 1 }}>
                  {labels.map((label) => (
                    <Chip key={label} size="small" label={label} variant="outlined" sx={{ height: 20, fontSize: fontSizes.xs }} />
                  ))}
                </Stack>
              )}
              <TableContainer sx={{ overflowX: "auto" }}>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell sx={{ fontSize: fontSizes.sm, color: terminalColors.gray, py: 0.5 }}>{t("viewer.colLabel")}</TableCell>
                      <TableCell sx={{ fontSize: fontSizes.sm, color: terminalColors.gray, py: 0.5 }}>{t("viewer.colEvidence")}</TableCell>
                      <TableCell sx={{ fontSize: fontSizes.sm, color: terminalColors.gray, py: 0.5 }}>{t("viewer.colDimension")}</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {entry.items.map((item, idx) => (
                      <TableRow key={idx}>
                        <TableCell sx={{ fontSize: fontSizes.md, py: 0.5, wordBreak: "break-word" }}>{item.name}</TableCell>
                        <TableCell
                          sx={{
                            fontSize: fontSizes.md,
                            py: 0.5,
                            color: terminalColors.gray,
                            wordBreak: "break-word",
                            overflowWrap: "anywhere",
                          }}
                        >
                          {item.evidence ?? "—"}
                        </TableCell>
                        <TableCell sx={{ fontSize: fontSizes.md, py: 0.5, wordBreak: "break-word" }}>
                          {item.normalized_label ?? "—"}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </AccordionDetails>
          </Accordion>
        );
      })}
    </Stack>
  );
}

function CorpusTab({ preview, total }: { preview: WorkspaceOverview["corpus_preview"]; total: unknown }) {
  const { t } = useI18n();
  if (preview.length === 0) {
    return (
      <Alert severity="info" variant="outlined">
        {t("viewer.corpusEmpty")}
      </Alert>
    );
  }

  return (
    <Stack spacing={1}>
      <Typography sx={{ fontSize: fontSizes.sm, color: terminalColors.gray }}>
        {t("viewer.corpusCount", { total: statNumber(total), count: preview.length })}
      </Typography>
      <List dense disablePadding>
        {preview.map((item) => (
          <ListItem
            key={item.id}
            disablePadding
            sx={{
              py: 0.75,
              borderBottom: `1px solid ${terminalColors.border}`,
              alignItems: "flex-start",
            }}
          >
            <Chip
              size="small"
              label={item.id}
              sx={{ height: 20, fontSize: fontSizes.xs, fontFamily: monoFont, mr: 1, mt: 0.25, flexShrink: 0 }}
            />
            <ListItemText
              primary={item.text}
              primaryTypographyProps={{
                fontSize: fontSizes.md,
                color: terminalColors.text,
                sx: { whiteSpace: "pre-wrap", wordBreak: "break-word", overflowWrap: "anywhere" },
              }}
            />
          </ListItem>
        ))}
      </List>
    </Stack>
  );
}

function EvalSection({
  title,
  payload,
}: {
  title: string;
  payload: Record<string, unknown> | null;
}) {
  const { t } = useI18n();
  const metrics = extractEvalMetrics(payload);

  if (!payload) {
    return (
      <Box>
        <Typography sx={{ fontWeight: 600, fontSize: fontSizes.lg, mb: 1 }}>{title}</Typography>
        <Alert severity="info" variant="outlined">
          {t("viewer.evalEmpty")}
        </Alert>
      </Box>
    );
  }

  return (
    <Box>
      <Typography sx={{ fontWeight: 600, fontSize: fontSizes.lg, mb: 1 }}>{title}</Typography>
      <Stack direction="row" flexWrap="wrap" useFlexGap gap={0.5} sx={{ mb: 1.5 }}>
        {typeof payload.status === "string" && (
          <Chip size="small" label={t("viewer.evalStatus", { status: payload.status })} sx={{ height: 22, fontSize: fontSizes.xs }} />
        )}
        {typeof payload.mode === "string" && (
          <Chip size="small" label={t("viewer.evalMode", { mode: payload.mode })} sx={{ height: 22, fontSize: fontSizes.xs }} />
        )}
        {typeof payload.coded_count === "number" && (
          <Chip size="small" label={t("viewer.evalCoded", { count: payload.coded_count })} sx={{ height: 22, fontSize: fontSizes.xs }} />
        )}
      </Stack>
      {metrics.length === 0 ? (
        <Alert severity="info" variant="outlined">
          {t("viewer.evalNoMacro")}
        </Alert>
      ) : (
        <Stack spacing={1.5}>
          {metrics.map((m) => {
            const hasItems = (m.both && m.both.length > 0) || (m.llmOnly && m.llmOnly.length > 0) || (m.humanOnly && m.humanOnly.length > 0);
            return (
              <Card key={m.labelKey} sx={cardSx}>
                <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
                  <Typography sx={{ fontSize: fontSizes.md, fontWeight: 600, mb: 1 }}>{t(m.labelKey)}</Typography>
                  <Stack direction="row" flexWrap="wrap" useFlexGap gap={1.5} sx={{ mb: hasItems ? 1.5 : 0 }}>
                    {m.consistency !== undefined && (
                      <Box>
                        <Typography sx={{ fontSize: "1.1rem", fontWeight: 700, color: terminalColors.green, fontFamily: monoFont }}>
                          {(m.consistency * 100).toFixed(1)}%
                        </Typography>
                        <Typography sx={{ fontSize: fontSizes.sm, color: terminalColors.gray }}>Consistency</Typography>
                      </Box>
                    )}
                    {m.precision !== undefined && (
                      <Box>
                        <Typography sx={{ fontSize: "1.1rem", fontWeight: 700, color: terminalColors.cyan, fontFamily: monoFont }}>
                          {(m.precision * 100).toFixed(1)}%
                        </Typography>
                        <Typography sx={{ fontSize: fontSizes.sm, color: terminalColors.gray }}>Precision</Typography>
                      </Box>
                    )}
                    {m.recall !== undefined && (
                      <Box>
                        <Typography sx={{ fontSize: "1.1rem", fontWeight: 700, color: terminalColors.magenta, fontFamily: monoFont }}>
                          {(m.recall * 100).toFixed(1)}%
                        </Typography>
                        <Typography sx={{ fontSize: fontSizes.sm, color: terminalColors.gray }}>Recall</Typography>
                      </Box>
                    )}
                  </Stack>
                  {hasItems && (
                    <Stack spacing={1}>
                      {m.both && m.both.length > 0 && (
                        <Box>
                          <Typography sx={{ fontSize: fontSizes.sm, color: terminalColors.gray, mb: 0.5 }}>
                            {t("viewer.matchBoth", { count: m.both.length })}
                          </Typography>
                          <Stack direction="row" flexWrap="wrap" useFlexGap gap={0.5}>
                            {m.both.map((item) => (
                              <Chip
                                key={item}
                                size="small"
                                label={item}
                                sx={{
                                  height: 20,
                                  fontSize: fontSizes.xs,
                                  bgcolor: "rgba(63, 185, 80, 0.12)",
                                  borderColor: "rgba(63, 185, 80, 0.4)",
                                  color: terminalColors.green,
                                }}
                                variant="outlined"
                              />
                            ))}
                          </Stack>
                        </Box>
                      )}
                      {m.llmOnly && m.llmOnly.length > 0 && (
                        <Box>
                          <Typography sx={{ fontSize: fontSizes.sm, color: terminalColors.gray, mb: 0.5 }}>
                            {t("viewer.matchAgentOnly", { count: m.llmOnly.length })}
                          </Typography>
                          <Stack direction="row" flexWrap="wrap" useFlexGap gap={0.5}>
                            {m.llmOnly.map((item) => (
                              <Chip
                                key={item}
                                size="small"
                                label={item}
                                sx={{
                                  height: 20,
                                  fontSize: fontSizes.xs,
                                  bgcolor: "rgba(57, 197, 207, 0.1)",
                                  borderColor: "rgba(57, 197, 207, 0.35)",
                                  color: terminalColors.cyan,
                                }}
                                variant="outlined"
                              />
                            ))}
                          </Stack>
                        </Box>
                      )}
                      {m.humanOnly && m.humanOnly.length > 0 && (
                        <Box>
                          <Typography sx={{ fontSize: fontSizes.sm, color: terminalColors.gray, mb: 0.5 }}>
                            {t("viewer.matchHumanOnly", { count: m.humanOnly.length })}
                          </Typography>
                          <Stack direction="row" flexWrap="wrap" useFlexGap gap={0.5}>
                            {m.humanOnly.map((item) => (
                              <Chip
                                key={item}
                                size="small"
                                label={item}
                                sx={{
                                  height: 20,
                                  fontSize: fontSizes.xs,
                                  bgcolor: "rgba(210, 153, 34, 0.1)",
                                  borderColor: "rgba(210, 153, 34, 0.4)",
                                  color: terminalColors.yellow,
                                }}
                                variant="outlined"
                              />
                            ))}
                          </Stack>
                        </Box>
                      )}
                    </Stack>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </Stack>
      )}
    </Box>
  );
}

function EvalTab({ data }: { data: WorkspaceOverview }) {
  const { t } = useI18n();
  return (
    <Stack spacing={2} divider={<Divider sx={{ borderColor: terminalColors.border }} />}>
      <EvalSection title={t("viewer.evalOpenTitle")} payload={data.eval_open} />
      <EvalSection title={t("viewer.evalAxialTitle")} payload={data.eval_axial} />
    </Stack>
  );
}

export function WorkspaceViewer({ sessionId, open, onClose }: WorkspaceViewerProps) {
  const { t } = useI18n();
  const [tabIndex, setTabIndex] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<WorkspaceOverview | null>(null);

  useEffect(() => {
    if (!open) {
      setData(null);
      setError(null);
      setTabIndex(0);
      return;
    }
    setLoading(true);
    setError(null);
    void getWorkspaceOverview(sessionId)
      .then(setData)
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : t("viewer.loadFailed"));
      })
      .finally(() => setLoading(false));
  }, [open, sessionId, t]);

  return (
    <Dialog
      open={open}
      onClose={onClose}
      fullWidth
      maxWidth="md"
      PaperProps={{
        sx: {
          height: "82vh",
          maxHeight: "82vh",
          display: "flex",
          flexDirection: "column",
          m: 2,
        },
      }}
    >
      <DialogTitle sx={{ pb: 1, flexShrink: 0 }}>{t("viewer.title")}</DialogTitle>
      <DialogContent
        sx={{
          p: 0,
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
          flex: 1,
        }}
      >
        {loading && (
          <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}>
            <CircularProgress size={28} />
          </Box>
        )}
        {error && (
          <Alert severity="error" sx={{ m: 2, mb: 0 }}>
            {error}
          </Alert>
        )}
        {!loading && !error && data && (
          <>
            <Tabs
              value={tabIndex}
              onChange={(_, next) => setTabIndex(next)}
              sx={{
                px: 2,
                borderBottom: `1px solid ${terminalColors.border}`,
                flexShrink: 0,
              }}
              variant="scrollable"
              scrollButtons="auto"
            >
              {TAB_KEYS.map((key) => (
                <Tab key={key} label={t(key)} sx={{ fontSize: fontSizes.md, minHeight: 40 }} />
              ))}
            </Tabs>
            <Box
              sx={{
                flex: 1,
                overflowY: "auto",
                overflowX: "hidden",
                px: 2,
                py: 2,
              }}
            >
              {tabIndex === 0 && <OverviewTab data={data} />}
              {tabIndex === 1 && <CodebookTab dimensions={data.dimensions} />}
              {tabIndex === 2 && <CodingTab coding={data.coding} />}
              {tabIndex === 3 && (
                <CorpusTab
                  preview={data.corpus_preview}
                  total={data.status.texts_total ?? data.corpus_preview.length}
                />
              )}
              {tabIndex === 4 && <EvalTab data={data} />}
            </Box>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
