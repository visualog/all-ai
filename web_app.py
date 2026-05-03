#!/usr/bin/env python3
"""Local web UI for the all-ai research workbench."""

from __future__ import annotations

import argparse
import html
import threading
import urllib.parse
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import all_ai


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765


def form_value(fields: dict[str, list[str]], name: str, default: str = "") -> str:
    return fields.get(name, [default])[0].strip()


def textarea(value: str) -> str:
    return html.escape(value, quote=False)


def render_page(topic_file: Path, notice: str = "", error: str = "") -> str:
    exists = topic_file.exists()
    if exists:
        state = all_ai.load_state(topic_file)
        next_agent = all_ai.next_agent(state, None)
        current_prompt = all_ai.build_prompt(state, next_agent)
        topic = state.topic
        turns = len(state.turns)
        memory = state.content
    else:
        next_agent = "architect"
        current_prompt = ""
        topic = ""
        turns = 0
        memory = "No topic yet. Start by creating one."

    agent_options = "\n".join(
        f'<option value="{agent}">{agent}</option>' for agent in all_ai.AGENT_ORDER
    )

    notice_html = f'<div class="notice">{html.escape(notice)}</div>' if notice else ""
    error_html = f'<div class="error">{html.escape(error)}</div>' if error else ""
    disabled = "" if exists else "disabled"

    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>all-ai workbench</title>
  <style>
    :root {{
      --ink: #252016;
      --muted: #746a5b;
      --paper: #f6efe1;
      --panel: #fff8ea;
      --line: #d9c7a8;
      --accent: #b94f27;
      --accent-dark: #73331d;
      --sage: #536b4d;
      --blueprint: #25384f;
      --shadow: 0 22px 60px rgba(70, 48, 22, .16);
      font-family: ui-serif, "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      background:
        radial-gradient(circle at 12% 8%, rgba(185, 79, 39, .22), transparent 28rem),
        radial-gradient(circle at 88% 18%, rgba(83, 107, 77, .18), transparent 24rem),
        linear-gradient(135deg, #fbf4e8 0%, var(--paper) 48%, #ece0ca 100%);
      min-height: 100vh;
    }}
    body:before {{
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      background-image:
        linear-gradient(rgba(80, 57, 30, .045) 1px, transparent 1px),
        linear-gradient(90deg, rgba(80, 57, 30, .045) 1px, transparent 1px);
      background-size: 26px 26px;
      mask-image: linear-gradient(to bottom, black, transparent 82%);
    }}
    .shell {{
      width: min(1440px, calc(100% - 32px));
      margin: 0 auto;
      padding: clamp(22px, 4vw, 56px) 0;
    }}
    header {{
      display: grid;
      grid-template-columns: minmax(0, 1.2fr) minmax(280px, .8fr);
      gap: clamp(18px, 4vw, 56px);
      align-items: end;
      margin-bottom: 28px;
    }}
    h1 {{
      font-size: clamp(46px, 8vw, 112px);
      line-height: .86;
      letter-spacing: -.065em;
      margin: 0;
      max-width: 900px;
    }}
    .subtitle {{
      font-size: clamp(17px, 2vw, 25px);
      line-height: 1.35;
      color: var(--muted);
      margin: 18px 0 0;
      max-width: 720px;
    }}
    .status-card {{
      background: color-mix(in srgb, var(--panel) 88%, white);
      border: 1px solid var(--line);
      box-shadow: var(--shadow);
      padding: 22px;
      transform: rotate(.7deg);
    }}
    .status-card b {{
      display: block;
      font-size: 13px;
      text-transform: uppercase;
      letter-spacing: .12em;
      color: var(--accent-dark);
      margin-bottom: 10px;
    }}
    .status-card p {{ margin: 8px 0; color: var(--muted); }}
    .notice, .error {{
      margin: 16px 0;
      padding: 14px 16px;
      border: 1px solid;
      background: var(--panel);
    }}
    .notice {{ border-color: rgba(83, 107, 77, .45); color: var(--sage); }}
    .error {{ border-color: rgba(185, 79, 39, .5); color: var(--accent-dark); }}
    .grid {{
      display: grid;
      grid-template-columns: minmax(320px, .82fr) minmax(420px, 1.18fr);
      gap: 22px;
      align-items: start;
    }}
    .stack {{ display: grid; gap: 18px; }}
    section {{
      background: rgba(255, 248, 234, .86);
      border: 1px solid var(--line);
      box-shadow: 0 16px 38px rgba(80, 57, 30, .09);
      padding: clamp(18px, 2vw, 26px);
      position: relative;
    }}
    section:nth-child(2n) {{ background: rgba(247, 237, 216, .86); }}
    h2 {{
      margin: 0 0 14px;
      font-size: 24px;
      letter-spacing: -.02em;
    }}
    label {{
      display: block;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .12em;
      color: var(--muted);
      margin: 14px 0 7px;
    }}
    input, textarea, select {{
      width: 100%;
      border: 1px solid color-mix(in srgb, var(--line), var(--ink) 14%);
      background: #fffaf0;
      color: var(--ink);
      padding: 12px 13px;
      font: 15px/1.45 ui-monospace, "SF Mono", Menlo, Consolas, monospace;
      outline: none;
    }}
    textarea {{ min-height: 160px; resize: vertical; }}
    input:focus, textarea:focus, select:focus {{
      border-color: var(--accent);
      box-shadow: 0 0 0 3px rgba(185, 79, 39, .14);
    }}
    button, .link-button {{
      appearance: none;
      border: 1px solid var(--ink);
      background: var(--ink);
      color: #fff8ea;
      padding: 11px 15px;
      font: 700 13px/1 ui-monospace, "SF Mono", Menlo, Consolas, monospace;
      letter-spacing: .02em;
      cursor: pointer;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 42px;
    }}
    button:hover, .link-button:hover {{ transform: translateY(-1px); }}
    button.secondary, .link-button.secondary {{
      background: transparent;
      color: var(--ink);
    }}
    button:disabled {{
      opacity: .45;
      cursor: not-allowed;
      transform: none;
    }}
    .row {{ display: flex; gap: 10px; flex-wrap: wrap; align-items: end; }}
    .row > * {{ flex: 1 1 150px; }}
    .prompt-box textarea {{ min-height: 520px; }}
    .memory {{
      white-space: pre-wrap;
      max-height: 520px;
      overflow: auto;
      background: #fffaf0;
      border: 1px solid var(--line);
      padding: 16px;
      font: 13px/1.55 ui-monospace, "SF Mono", Menlo, Consolas, monospace;
    }}
    .micro {{
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
    }}
    @media (max-width: 980px) {{
      header, .grid {{ grid-template-columns: 1fr; }}
      .status-card {{ transform: none; }}
      .prompt-box textarea {{ min-height: 360px; }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <header>
      <div>
        <h1>Research<br>Workbench</h1>
        <p class="subtitle">AI들을 웹 채팅 자동화로 억지 연결하지 않고, 공유 메모리와 로컬 모델로 안전하게 사고를 굴리는 지휘판입니다.</p>
      </div>
      <aside class="status-card">
        <b>Current Loop</b>
        <p><strong>Topic:</strong> {html.escape(topic or "Not started")}</p>
        <p><strong>Turns:</strong> {turns}</p>
        <p><strong>Next agent:</strong> {html.escape(next_agent)}</p>
        <p><strong>File:</strong> {html.escape(str(topic_file))}</p>
      </aside>
    </header>

    {notice_html}
    {error_html}

    <div class="grid">
      <div class="stack">
        <section>
          <h2>Start Or Reset</h2>
          <form method="post" action="/init">
            <label for="topic">Topic</label>
            <textarea id="topic" name="topic" placeholder="탐구할 주제를 입력하세요.">{textarea(topic)}</textarea>
            <button type="submit">Create Topic</button>
          </form>
          <p class="micro">기존 `workbench/topic.md`를 새 주제로 덮어씁니다. 중요한 로그는 먼저 저장소에 커밋해 두는 편이 좋아요.</p>
        </section>

        <section>
          <h2>Add External Answer</h2>
          <form method="post" action="/add">
            <label for="agent">Agent name</label>
            <input id="agent" name="agent" value="Manual AI">
            <label for="response">Response</label>
            <textarea id="response" name="response" placeholder="ChatGPT/Gemini/Perplexity 등에서 사람이 직접 받은 답변을 여기에 붙여넣으세요."></textarea>
            <button type="submit" {disabled}>Record Answer</button>
          </form>
        </section>

        <section>
          <h2>Local Ollama</h2>
          <form method="post" action="/run-local">
            <div class="row">
              <div>
                <label for="model">Model</label>
                <input id="model" name="model" value="qwen2.5:7b">
              </div>
              <div>
                <label for="rounds">Rounds</label>
                <input id="rounds" name="rounds" value="1">
              </div>
            </div>
            <div class="row">
              <div>
                <label for="timeout">Timeout seconds</label>
                <input id="timeout" name="timeout" value="120">
              </div>
              <div>
                <label for="max_tokens">Max tokens</label>
                <input id="max_tokens" name="max_tokens" value="800">
              </div>
            </div>
            <button type="submit" {disabled}>Run Local Agent</button>
          </form>
          <p class="micro">Ollama 서버가 켜져 있어야 합니다. 실행 중에는 페이지 응답이 잠시 멈출 수 있습니다.</p>
        </section>
      </div>

      <div class="stack">
        <section class="prompt-box">
          <h2>Next Prompt</h2>
          <form method="get" action="/copy-prompt">
            <label for="agent_select">Agent</label>
            <select id="agent_select" name="agent">{agent_options}</select>
            <label for="prompt">Prompt</label>
            <textarea id="prompt" readonly>{textarea(current_prompt)}</textarea>
          </form>
          <div class="row">
            <a class="link-button" href="/prompt.txt">Open Prompt Text</a>
            <a class="link-button secondary" href="/export">Export Synthesis Prompt</a>
          </div>
          <p class="micro">브라우저 보안 때문에 자동 클립보드는 일부 환경에서 막힐 수 있어, 텍스트 영역을 클릭해 전체 선택 후 복사하면 됩니다.</p>
        </section>

        <section>
          <h2>Shared Memory</h2>
          <div class="memory">{textarea(memory)}</div>
        </section>
      </div>
    </div>
  </main>
</body>
</html>"""


class WorkbenchHandler(BaseHTTPRequestHandler):
    topic_file: Path = all_ai.DEFAULT_TOPIC_FILE

    def log_message(self, format: str, *args: object) -> None:
        return

    def read_form(self) -> dict[str, list[str]]:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        return urllib.parse.parse_qs(body, keep_blank_values=True)

    def send_html(self, html_body: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = html_body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_text(self, text: str, filename: str = "prompt.txt") -> None:
        body = text.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Disposition", f'inline; filename="{filename}"')
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def redirect_home(self, notice: str = "", error: str = "") -> None:
        query = urllib.parse.urlencode({"notice": notice, "error": error})
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", f"/?{query}")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        notice = form_value(query, "notice")
        error = form_value(query, "error")

        try:
            if parsed.path == "/":
                self.send_html(render_page(self.topic_file, notice=notice, error=error))
            elif parsed.path == "/prompt.txt":
                state = all_ai.load_state(self.topic_file)
                prompt = all_ai.build_prompt(state, all_ai.next_agent(state, None))
                self.send_text(prompt, "next-prompt.txt")
            elif parsed.path == "/export":
                state = all_ai.load_state(self.topic_file)
                prompt = "\n".join(
                    [
                        "Create a final synthesis from this shared memory.",
                        "",
                        all_ai.compact_memory(state.content, limit=22000),
                    ]
                )
                self.send_text(prompt, "synthesis-prompt.txt")
            else:
                self.send_error(HTTPStatus.NOT_FOUND)
        except Exception as exc:  # The UI should show recoverable app errors.
            self.send_html(render_page(self.topic_file, error=str(exc)), HTTPStatus.INTERNAL_SERVER_ERROR)

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        fields = self.read_form()
        try:
            if parsed.path == "/init":
                topic = form_value(fields, "topic")
                if not topic:
                    raise ValueError("Topic is required.")
                all_ai.init_topic(type("Args", (), {"file": str(self.topic_file), "topic": topic, "force": True}))
                self.redirect_home("Topic created.")
            elif parsed.path == "/add":
                agent = form_value(fields, "agent", "Manual AI")
                response = form_value(fields, "response")
                all_ai.add_turn(
                    type(
                        "Args",
                        (),
                        {
                            "file": str(self.topic_file),
                            "agent": agent,
                            "response_file": None,
                            "response": response,
                        },
                    )
                )
                self.redirect_home("Answer recorded.")
            elif parsed.path == "/run-local":
                model = form_value(fields, "model", "qwen2.5:7b")
                rounds = int(form_value(fields, "rounds", "1"))
                timeout = int(form_value(fields, "timeout", "120"))
                max_tokens_text = form_value(fields, "max_tokens", "800")
                max_tokens = int(max_tokens_text) if max_tokens_text else None
                all_ai.run_local(
                    type(
                        "Args",
                        (),
                        {
                            "file": str(self.topic_file),
                            "model": model,
                            "rounds": rounds,
                            "ollama_url": all_ai.DEFAULT_OLLAMA_URL,
                            "temperature": 0.7,
                            "timeout": timeout,
                            "max_tokens": max_tokens,
                        },
                    )
                )
                self.redirect_home("Local agent finished.")
            else:
                self.send_error(HTTPStatus.NOT_FOUND)
        except Exception as exc:
            self.redirect_home(error=str(exc))


def build_server(host: str, port: int, topic_file: Path) -> ThreadingHTTPServer:
    class Handler(WorkbenchHandler):
        pass

    Handler.topic_file = topic_file
    return ThreadingHTTPServer((host, port), Handler)


def main() -> int:
    parser = argparse.ArgumentParser(description="Local web UI for all-ai")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--file", default=str(all_ai.DEFAULT_TOPIC_FILE))
    parser.add_argument("--no-open", action="store_true", help="Do not open the browser automatically")
    args = parser.parse_args()

    server = build_server(args.host, args.port, Path(args.file))
    url = f"http://{args.host}:{args.port}"
    print(f"all-ai web UI running at {url}", flush=True)
    print("Press Ctrl+C to stop.", flush=True)
    if not args.no_open:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        threading.Thread(target=server.shutdown, daemon=True).start()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
