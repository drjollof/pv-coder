# PV-Coder Project Rules

## Code Style — No Trivial Comments

When writing, editing, or generating any code in this repository, **all models must strictly follow these rules**:

- **No numbered steps.** Never write `# 1. Extract entities`, `# 2. Normalize`, `# Step 3: ...` or any numbered section headers in code.
- **No narrating comments.** Never write a comment that simply re-states what the next line does. If the code is `results.append(case)`, do not write `# Append case to results` above it.
- **No conversational language.** Comments must contain zero references to instructions, prompts, users, or the AI interaction context. No "For MVP", "per the plan", "the user wants", or "we will do X".
- **No "TODO" placeholders** unless they describe a specific, actionable engineering task.
- **Only comment on non-obvious "why" logic** — e.g. a regex pattern's intent, a numerical threshold's regulatory basis, or a workaround for a known library limitation.

This rule applies to every file extension: `.py`, `.jsx`, `.ts`, `.css`, `.md` (inline code). It applies to every editing operation: new files, edits, refactors, and code reviews.
