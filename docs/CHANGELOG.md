# Changelog

This changelog tracks product and implementation changes for Jon's Gradebook.

## Entry Format

Each entry should include:
- date (YYYY-MM-DD)
- git commit hash (short SHA)
- area(s) changed
- concise summary

Template:

```md
## YYYY-MM-DD
- [commit abc1234] [area: canvas-sync] Summary of change.
- [commit def5678] [area: gradebook] Summary of change.
```

If work is not committed yet, use `commit WORKTREE` temporarily and replace it after commit.

---

## 2026-04-22
- [commit 0b34447] [area: backup] Added backup restore preflight comparison endpoint and related restore-safety workflow support.
- [commit 0b34447] [area: migrations] Fixed calculated column migration conflict by avoiding duplicate PostgreSQL enum type creation.
- [commit 2344148] [area: gradebook] Added right-side collapsible details pane and editor options toggles.
- [commit d146e49] [area: gradebook] Added completion quick edits and 4-state keyboard cycle (Complete -> Incomplete -> Missing -> Excused).
- [commit d146e49] [area: gradebook] Added drag-and-drop column reordering with optional arrow controls.
- [commit d146e49] [area: students] Replaced Students card list with searchable/sortable grid and all/in-classes/advisees filters.
- [commit d146e49] [area: students] Added editable profile fields for first name, last name, email, and phone number.
- [commit fb8a39f] [area: canvas-sync] Reorganized page into collapsible sections and added class picker filter/paging controls.
- [commit fb8a39f] [area: canvas-sync] Clarified class selection actions: replace allowlist vs add-to-allowlist.
- [commit 33c9031] [area: docs] Added V1 QA checklist and updated implementation/README docs for current V1 status tracking.
- [commit WORKTREE] [area: docs] Marked V1 complete and set V2 workflow hardening as active phase in plan/README.
