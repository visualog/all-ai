#!/usr/bin/env python3
"""Policy-safe multi-agent research workbench.

The CLI stores a shared Markdown memory and can either generate prompts for
manual use or run local Ollama agents without touching commercial web UIs.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import textwrap
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path


DEFAULT_WORKSPACE = Path("workbench")
DEFAULT_TOPIC_FILE = DEFAULT_WORKSPACE / "topic.md"
DEFAULT_OLLAMA_URL = "http://localhost:11434/api/generate"

AGENT_ORDER = ["architect", "explorer", "researcher", "skeptic", "synthesizer", "scribe"]

AGENTS: dict[str, str] = {
    "architect": (
        "You structure the investigation. Reframe the topic, expose hidden "
        "assumptions, separate sub-questions, and keep the team from drifting."
    ),
    "explorer": (
        "You expand the possibility space. Add alternative hypotheses, unusual "
        "angles, analogies, and productive tensions without forcing a conclusion."
    ),
    "researcher": (
        "You identify what needs evidence. Propose search queries, source types, "
        "verification criteria, and mark claims that should not be trusted yet."
    ),
    "skeptic": (
        "You are constructively critical. Find weak logic, missing counterexamples, "
        "overconfident claims, and places where the team is agreeing too easily."
    ),
    "synthesizer": (
        "You integrate. Preserve the strongest disagreements, update the working "
        "hypothesis, and convert scattered ideas into a clearer model."
    ),
    "scribe": (
        "You maintain memory. Summarize the durable takeaways, unresolved questions, "
        "and the best next prompt for the following round."
    ),
}

PROMPT_TEMPLATE = """\
You are one member of an independent AI research team.

Shared goal:
Develop the topic through hypothesis, evidence, critique, rebuttal, reconstruction,
and further investigation. Do not merely answer once. Improve the team's thinking.

Your role:
{role_name}
{role_description}

Current shared memory:
{memory}

Your task for this turn:
1. Add one or more new contributions.
2. Identify the evidence that supports them, or state what evidence is still needed.
3. Critique at least one existing claim or assumption.
4. Reconstruct the topic into a stronger working hypothesis.
5. Hand off 3 precise questions to the next agent.

Output format:
## New Contribution
...

## Evidence / Evidence Needed
...

## Critique
...

## Reconstructed Hypothesis
...

## Questions For Next Agent
1. ...
2. ...
3. ...
"""


@dataclass
class TopicState:
    path: Path
    topic: str
    turns: list[str]
    content: str


def now_stamp() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9가-힣_-]+", "-", value.strip()).strip("-")
    return slug[:64] or "topic"


def read_text(path: Path) -> str:
    if not path.exists():
        raise SystemExit(f"Topic file not found: {path}. Run `python3 all_ai.py init \"topic\"` first.")
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def load_state(path: Path) -> TopicState:
    content = read_text(path)
    topic_match = re.search(r"^# Topic\n\n(.+?)\n", content, flags=re.MULTILINE | re.DOTALL)
    topic = topic_match.group(1).strip() if topic_match else "Untitled topic"
    turns = re.findall(r"^## Turn \d+ - (.+?)$", content, flags=re.MULTILINE)
    return TopicState(path=path, topic=topic, turns=turns, content=content)


def next_agent(state: TopicState, requested: str | None) -> str:
    if requested:
        key = requested.lower()
        if key not in AGENTS:
            valid = ", ".join(AGENT_ORDER)
            raise SystemExit(f"Unknown agent `{requested}`. Valid agents: {valid}")
        return key
    return AGENT_ORDER[len(state.turns) % len(AGENT_ORDER)]


def compact_memory(content: str, limit: int = 14000) -> str:
    if len(content) <= limit:
        return content
    head = content[:2500]
    tail = content[-(limit - len(head) - 120) :]
    return f"{head}\n\n[...older middle content omitted for prompt size...]\n\n{tail}"


def build_prompt(state: TopicState, agent: str) -> str:
    return PROMPT_TEMPLATE.format(
        role_name=agent,
        role_description=AGENTS[agent],
        memory=compact_memory(state.content),
    )


def init_topic(args: argparse.Namespace) -> None:
    path = Path(args.file)
    if path.exists() and not args.force:
        raise SystemExit(f"{path} already exists. Use --force to overwrite.")

    content = f"""# Topic

{args.topic}

# Operating Principles

- Do not automate or scrape commercial web chat UIs.
- Manual mode is allowed: a human submits prompts and adds answers back here.
- Local mode may run unattended against local models such as Ollama.
- Each turn should add claims, evidence needs, critique, reconstruction, and handoff questions.

# Working Hypothesis

To be developed.

# Claims

- Pending.

# Evidence

- Pending.

# Counterarguments

- Pending.

# Open Questions

- Pending.

# Conversation

"""
    write_text(path, content)
    print(f"Created {path}")


def print_prompt(args: argparse.Namespace) -> None:
    state = load_state(Path(args.file))
    agent = next_agent(state, args.agent)
    print(build_prompt(state, agent))


def add_turn(args: argparse.Namespace) -> None:
    path = Path(args.file)
    state = load_state(path)
    response_path = Path(args.response_file) if args.response_file else None
    if response_path:
        response = read_text(response_path).strip()
    else:
        response = sys.stdin.read().strip()
    if not response:
        raise SystemExit("No response provided. Use --response-file or pipe text on stdin.")

    turn_number = len(state.turns) + 1
    agent_name = args.agent.strip()
    entry = f"""## Turn {turn_number} - {agent_name}

Recorded: {now_stamp()}

{response}

"""
    with path.open("a", encoding="utf-8") as file:
        file.write(entry)
    print(f"Added turn {turn_number} from {agent_name} to {path}")


def call_ollama(prompt: str, model: str, url: str, temperature: float) -> str:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature},
    }
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise SystemExit(
            "Could not reach Ollama. Start it with `ollama serve`, pull a model, "
            f"then retry. Details: {exc}"
        ) from exc
    return str(body.get("response", "")).strip()


def run_local(args: argparse.Namespace) -> None:
    path = Path(args.file)
    for _ in range(args.rounds):
        state = load_state(path)
        agent = next_agent(state, None)
        print(f"Running {agent} with {args.model}...")
        prompt = build_prompt(state, agent)
        response = call_ollama(prompt, args.model, args.ollama_url, args.temperature)
        if not response:
            raise SystemExit("Ollama returned an empty response.")
        append_generated_turn(path, state, agent, args.model, response)


def append_generated_turn(path: Path, state: TopicState, agent: str, model: str, response: str) -> None:
    turn_number = len(state.turns) + 1
    entry = f"""## Turn {turn_number} - {agent} / {model}

Recorded: {now_stamp()}

{response}

"""
    with path.open("a", encoding="utf-8") as file:
        file.write(entry)
    print(f"Added turn {turn_number} from {agent}")


def export_summary(args: argparse.Namespace) -> None:
    state = load_state(Path(args.file))
    out = Path(args.output) if args.output else DEFAULT_WORKSPACE / f"{slugify(state.topic)}-export.md"
    prompt = textwrap.dedent(
        f"""\
        Use the conversation in `{state.path}` to create a final synthesis with:

        - strongest current hypothesis
        - key evidence and evidence gaps
        - strongest counterarguments
        - unresolved questions
        - recommended next research loop

        This command does not call a model. Paste the content below into a model
        manually, or run local rounds until the scribe creates this summary.

        ---

        {compact_memory(state.content, limit=22000)}
        """
    )
    write_text(out, prompt)
    print(f"Wrote export prompt to {out}")


def show_status(args: argparse.Namespace) -> None:
    state = load_state(Path(args.file))
    agent = next_agent(state, None)
    print(f"Topic: {state.topic}")
    print(f"Turns: {len(state.turns)}")
    print(f"Next agent: {agent}")
    print(f"File: {state.path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Multi-agent research workbench")
    parser.add_argument("--file", default=str(DEFAULT_TOPIC_FILE), help="Topic Markdown file")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Create a new topic workspace")
    init.add_argument("topic")
    init.add_argument("--force", action="store_true")
    init.set_defaults(func=init_topic)

    prompt = sub.add_parser("prompt", help="Print the next manual prompt")
    prompt.add_argument("--agent", choices=AGENT_ORDER)
    prompt.set_defaults(func=print_prompt)

    add = sub.add_parser("add", help="Add a manual response as a new turn")
    add.add_argument("--agent", required=True)
    add.add_argument("--response-file", "--file-in", dest="response_file")
    add.set_defaults(func=add_turn)

    run = sub.add_parser("run-local", help="Run one or more local Ollama turns")
    run.add_argument("--model", required=True)
    run.add_argument("--rounds", type=int, default=1)
    run.add_argument("--ollama-url", default=os.environ.get("OLLAMA_URL", DEFAULT_OLLAMA_URL))
    run.add_argument("--temperature", type=float, default=0.7)
    run.set_defaults(func=run_local)

    export = sub.add_parser("export", help="Write a final synthesis prompt")
    export.add_argument("--output")
    export.set_defaults(func=export_summary)

    status = sub.add_parser("status", help="Show topic status")
    status.set_defaults(func=show_status)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
