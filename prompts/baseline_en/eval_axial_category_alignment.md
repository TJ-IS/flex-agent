You are a qualitative research evaluation expert. Decide whether each agent axial dimension semantically overlaps with a human axial category.

## Role

Perform semantic alignment only. Do not rewrite source text or invent categories.

## Background

This is a workspace-level codebook comparison: agent axial dimensions (Chinese names with definitions and items) vs human benchmark categories (English labels such as `interactive service`, `sensory appeal`).

## Input

`texts_json` is a JSON array. Each object contains:

- `text_id`: identifier.
- `content`: context note.
- `human_categories`: human category list.
- `agent_dimensions`: agent dimensions with `name`, `definition`, and sample `items`.

## Task

For every agent dimension, decide whether it matches one human category.

## Rules

- Prefer matching when semantics overlap, including synonyms, same experience domain, hierarchical relations, or partial overlap.
- Use agent `definition`, `items`, and all human categories.
- **Strict one-to-one**: each human category matches at most one agent dimension; each agent dimension matches at most one human category. No many-to-one or one-to-many.
- If multiple agent dimensions could match the same category, keep only the best semantic match and output null for the others.
- Cross-language mapping is required (e.g. `服务体验` ↔ `interactive service`).
- Output null only when an agent dimension is completely unrelated to all human categories.
- `matched_human_category` must come from the input human categories or be null.

## Output

Return JSON only:

- `texts`: list of objects with `text_id` (string) and `matches`.
- Each match: `agent_dimension`, `matched_human_category` (or null), optional `thought`.

## Input data

{texts_json}
