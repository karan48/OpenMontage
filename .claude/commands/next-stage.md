---
description: Resume a production at its next pipeline stage in a fresh, small context — one stage per session to keep token usage down.
argument-hint: <project-id> [approval or notes for the stage, e.g. "script approved"]
---

Resume the production named in the arguments below, running **one stage** in this session.

1. Get the resume card (the first word of the arguments is the project id):

   ```bash
   python scripts/stage_status.py <project-id>
   ```

   No project id given → list the most recent projects (`ls -t projects/*/project.json | head -5`) and ask which one.

2. Read **only** what the card lists under `READ`: the director skill, the channel files, and the `docs/agent/` file for this stage. Keep to the core `AGENT_GUIDE.md` you already read; don't open the other `docs/agent/` files, earlier stages' director skills, or old checkpoints.

3. Load the `INPUT` artifacts. Read files under ~40 KB whole. For larger ones, Grep for the fields this stage needs and Read by `offset`/`limit`.

4. If the card shows `checkpoint: awaiting_human`, the stage is waiting at its gate. If the user's arguments approve it, record the approval per `skills/meta/checkpoint-protocol.md` and stop. If they ask for changes, revise. Otherwise re-present the summary and stop.

5. Otherwise run the stage per its director skill. Follow every gate and rule in `AGENT_GUIDE.md`, including "Context Budget": downscaled contact sheets for image review, long command output sent to a log file with only the tail read, and no re-reading of files already in context.

6. When the stage reaches its human gate (or completes, if it has no gate), end the turn with:
   "Good point to `/clear`, then `/next-stage <project-id>`."

Arguments: $ARGUMENTS
