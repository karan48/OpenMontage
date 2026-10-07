"""Print a compact resume card for a project, for starting a stage in a fresh session.

Long single-session runs re-send the whole context on every call, so the
cheap way to run a pipeline is one stage per session. This prints only what
the next stage needs: where the run is, which director skill to read, the
channel files, the previous stage's artifacts (with sizes, so large ones are
read by section) and the `docs/agent/` file for the stage.

    python scripts/stage_status.py <project-id>

Used by the `/next-stage` command. See AGENT_GUIDE.md -> "Context Budget".
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.checkpoint import get_completed_stages, get_next_stage, read_checkpoint  # noqa: E402
from lib.pipeline_loader import (  # noqa: E402
    get_stage_human_approval_default,
    get_stage_skill,
    load_pipeline,
)

PROJECTS = ROOT / "projects"

# docs/agent/ reference files each stage needs (AGENT_GUIDE.md -> "Where the Details Live").
STAGE_DOCS = {
    "research": ["governance.md"],
    "idea": ["preflight.md", "governance.md"],
    "proposal": ["preflight.md", "governance.md", "composition-runtimes.md"],
    "assets": ["layer-map.md"],
    "edit": ["composition-runtimes.md"],
    "compose": ["composition-runtimes.md"],
}


def _kb(path: Path) -> str:
    return f"{path.stat().st_size / 1024:.0f} KB"


def main(project_id: str) -> int:
    project_dir = PROJECTS / project_id
    marker = project_dir / "project.json"
    if not marker.exists():
        print(f"No project.json at {marker}")
        return 1
    project = json.loads(marker.read_text(encoding="utf-8"))
    pipeline = project.get("pipeline_type")
    manifest = load_pipeline(pipeline)
    stages = [s["name"] for s in manifest["stages"]]

    done = get_completed_stages(PROJECTS, project_id, pipeline)
    stage = get_next_stage(PROJECTS, project_id, pipeline)

    print(f"project:  {project_id} - {project.get('title', '')}")
    print(f"pipeline: {pipeline}   playbook: {project.get('style_playbook', '-')}")
    channel = project.get("channel")
    print(f"channel:  {channel or '-'}   format: {project.get('video_format', '-')}")
    print(f"done:     {', '.join(done) or '(none)'}")
    if stage is None:
        print("next:     all stages completed")
        return 0

    cp = read_checkpoint(PROJECTS, project_id, stage)
    status = cp.get("status") if cp else "not started"
    gated = get_stage_human_approval_default(manifest, stage)
    print(f"next:     {stage}   checkpoint: {status}   human gate: {'yes' if gated else 'no'}")

    skill = get_stage_skill(manifest, stage)
    if skill:
        print(f"\nREAD  director: skills/{skill}.md")
    if channel:
        for name in ("channel.yaml", "script-guide.md", "characters.md"):
            path = ROOT / "channels" / channel / name
            if path.exists():
                print(f"READ  channel:  {path.relative_to(ROOT).as_posix()}")
    for doc in STAGE_DOCS.get(stage, []):
        print(f"READ  guide:    docs/agent/{doc}")

    idx = stages.index(stage)
    if idx > 0:
        prev = stages[idx - 1]
        for name in next((s.get("produces", []) for s in manifest["stages"] if s["name"] == prev), []):
            path = project_dir / "artifacts" / f"{name}.json"
            if path.exists():
                size = _kb(path)
                hint = "  (large: read by section)" if path.stat().st_size > 40 * 1024 else ""
                print(f"INPUT {prev}: {path.relative_to(ROOT).as_posix()} [{size}]{hint}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__.strip().splitlines()[0])
        print("usage: python scripts/stage_status.py <project-id>")
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
