---
id: T-152
title: "Export diagrams to SVG/PNG"
epic: E15
priority: P1
depends_on: [T-150, T-151]
estimate: S
owner: agent
status: done
wave: 1
---

# T-152 — Export diagrams to SVG/PNG

**Epic:** E15 Assignment deliverables · **Priority:** P1 · **Estimate:** S · **Wave:** 1

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Submission needs images, not only Mermaid source.

## Scope
- Script `deliverables/diagrams/render.sh` renders every .mmd to .svg and .png (white background, width 2000).

## Files
- `deliverables/diagrams/render.sh`
- `deliverables/diagrams/*.svg`
- `deliverables/diagrams/*.png`

## Implementation notes
- Follow DECISIONS.md; no extra notes.

## Acceptance criteria
- [x] Each .mmd has matching .svg and .png.
- [x] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
bash deliverables/diagrams/render.sh && ls deliverables/diagrams/*.png
```

## Out of scope
- Anything not listed in Scope.

## Follow-ups
- mermaid-cli 12 has no width flag (`--size` caps the longest side, which shrank tall diagrams to ~720 px wide). `render.sh` disables `useMaxWidth` instead, so diagrams render at natural size: every PNG is ~1900 px wide or more with full-size text.
