# all-ai

Policy-safe multi-agent research workbench.

This project avoids automating commercial web chat UIs. Instead it supports:

- **Manual approval mode**: generate the next prompt, paste it into any AI service yourself, then add the answer back into the local workspace.
- **Local automation mode**: run a full multi-agent round against local Ollama models.

The core loop is:

```text
hypothesis -> evidence -> critique -> rebuttal -> reconstruction -> next questions
```

## Quick Start

```bash
python3 all_ai.py init "AI teams for deep research"
python3 all_ai.py prompt
python3 all_ai.py prompt --output next-prompt.md
python3 all_ai.py add --agent "External ChatGPT" --file answer.txt
python3 all_ai.py prompt --agent skeptic
python3 all_ai.py status
```

The default project file is created in `workbench/topic.md`.

## Local Ollama Mode

Install and run Ollama separately, then pull a model such as `qwen2.5:7b` or another model that works well on your machine.

```bash
ollama serve
ollama pull qwen2.5:7b
python3 all_ai.py run-local --model qwen2.5:7b --rounds 2 --timeout 120 --max-tokens 800
```

This talks only to `http://localhost:11434` by default.

## Commands

```bash
python3 all_ai.py init "topic"
python3 all_ai.py prompt --agent explorer
python3 all_ai.py add --agent "Gemini manual" --file response.md
python3 all_ai.py add --agent "Quick note" --response "A short manually added response."
python3 all_ai.py run-local --model qwen2.5:7b --rounds 1 --max-tokens 800
python3 all_ai.py export
python3 all_ai.py status
```

## Agent Roles

- `architect`: reframes the topic and maintains the research shape.
- `explorer`: expands promising directions and alternative hypotheses.
- `researcher`: identifies evidence needs, search queries, and source criteria.
- `skeptic`: challenges weak logic, hidden assumptions, and missing counterexamples.
- `synthesizer`: integrates the best claims into a stronger working model.
- `scribe`: records decisions, open questions, and the next loop.

## Safety Boundary

Do not use this tool to scrape, control, or extract outputs from commercial web chat UIs. If you use ChatGPT, Gemini, Perplexity, or similar web products, keep that interaction manual: you submit prompts and copy responses yourself.
