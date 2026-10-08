"""Record a real, captioned fixture walkthrough using isolated Playwright tools."""

import argparse
import hashlib
import json
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright


def capture(output, channel=None):
    repository = Path(__file__).resolve().parents[1]
    output.mkdir(parents=True, exist_ok=True)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    url = f"http://127.0.0.1:{port}"
    with tempfile.TemporaryDirectory(prefix="reco-demo-") as temporary:
        workspace = Path(temporary)
        with (workspace / "server.log").open("w+") as log:
            server = subprocess.Popen(
                [
                    str(repository / ".venv/bin/python"),
                    "-c",
                    "import sys, uvicorn; from reco.api import create_app; "
                    "uvicorn.run(create_app(), host='127.0.0.1', port=int(sys.argv[1]), "
                    "access_log=False)",
                    str(port),
                ],
                cwd=workspace,
                stdout=log,
                stderr=log,
            )
            try:
                deadline = time.monotonic() + 30
                while True:
                    try:
                        with urllib.request.urlopen(url + "/v1/model", timeout=2) as response:
                            model = json.load(response)
                        assert model["data_mode"] == "fictional_fixture"
                        break
                    except (OSError, urllib.error.URLError):
                        if server.poll() is not None or time.monotonic() >= deadline:
                            log.seek(0)
                            raise RuntimeError(log.read()) from None
                        time.sleep(0.1)
                errors = []
                responses = []
                with sync_playwright() as playwright:
                    browser = playwright.chromium.launch(headless=True, channel=channel)
                    browser_version = browser.version
                    context = browser.new_context(
                        viewport={"width": 1280, "height": 1000},
                        record_video_dir=str(workspace / "video"),
                        record_video_size={"width": 1280, "height": 1000},
                        reduced_motion="reduce",
                    )
                    context.route(
                        "**/*",
                        lambda route: (
                            route.continue_()
                            if route.request.url.startswith(url + "/")
                            else route.abort()
                        ),
                    )
                    page = context.new_page()
                    page.on("pageerror", lambda error: errors.append(str(error)))

                    def receive(response):
                        if response.url.endswith("/v1/recommendations"):
                            assert response.status == 200
                            responses.append(response.json())

                    page.on("response", receive)
                    page.goto(url, wait_until="networkidle")
                    assert "Fictional fixture" in page.locator("#mode").inner_text()
                    page.locator("#recommend").wait_for(state="visible")

                    def caption(text):
                        page.evaluate(
                            """text => {
                            let note = document.getElementById('demo-caption');
                            if (!note) {
                              note = document.createElement('div');
                              note.id = 'demo-caption';
                              note.style.cssText = 'position:fixed;bottom:12px;left:24px;'
                                +'right:24px;padding:14px 22px;background:#19332d;color:white;'
                                +'border-radius:10px;font:18px system-ui;z-index:1000;'
                                +'pointer-events:none';
                              document.body.append(note);
                            }
                            note.textContent = text;
                            }""",
                            text,
                        )

                    caption("CPU recommendation API · fictional fixture · no real quality claim")
                    page.wait_for_timeout(3500)
                    page.locator("#profile").select_option("1")
                    page.locator("#recommend").click()
                    page.wait_for_function(
                        "document.querySelector('#status').textContent"
                        ".startsWith('Comparison complete')"
                    )
                    assert len(responses) == 2
                    assert all(
                        not {1, 2, 3, 4, 5} & {hit["movie_id"] for hit in row["items"]}
                        for row in responses
                    )
                    caption(
                        "Saved profile: previously rated movies, including dislikes, are excluded"
                    )
                    page.locator(".results").scroll_into_view_if_needed()
                    page.wait_for_timeout(5000)
                    page.evaluate("document.getElementById('demo-caption').remove()")
                    page.screenshot(path=str(output / "fixture-demo.png"), full_page=True)
                    page.locator("#profile").scroll_into_view_if_needed()
                    catalog = context.request.get(url + "/v1/catalog").json()
                    for movie in catalog[:3]:
                        page.get_by_role(
                            "button", name="Like " + movie["title"], exact=True
                        ).click()
                        page.wait_for_timeout(650)
                    caption(
                        "Choose your own likes; preferences stay in the request and are never saved"
                    )
                    page.wait_for_timeout(3500)
                    genre = model["genres"][0]
                    page.locator("#genre").select_option(genre)
                    page.locator("#recommend").click()
                    page.wait_for_function(
                        "document.querySelector('#status').textContent"
                        ".startsWith('Comparison complete')"
                    )
                    assert len(responses) == 4
                    excluded = {movie["movie_id"] for movie in catalog[:3]}
                    assert all(
                        not excluded & {hit["movie_id"] for hit in row["items"]}
                        for row in responses[2:]
                    )
                    by_id = {movie["movie_id"]: movie for movie in catalog}
                    assert all(
                        genre in by_id[hit["movie_id"]]["genres"]
                        for row in responses[2:]
                        for hit in row["items"]
                    )
                    caption("Genre filters apply to both lists; popularity remains selected")
                    page.locator(".results").scroll_into_view_if_needed()
                    page.wait_for_timeout(5000)
                    page.locator("summary").click()
                    page.locator("#selection").scroll_into_view_if_needed()
                    caption(
                        "Validation selects the model. The final test never changes that decision"
                    )
                    page.wait_for_timeout(5000)
                    video = page.video
                    context.close()
                    video.save_as(str(output / "fixture-demo.webm"))
                    mobile = browser.new_context(viewport={"width": 390, "height": 844})
                    mobile_page = mobile.new_page()
                    mobile_page.on("pageerror", lambda error: errors.append(str(error)))
                    mobile_page.goto(url, wait_until="networkidle")
                    mobile_page.locator("#recommend").click()
                    mobile_page.wait_for_function(
                        "document.querySelector('#status').textContent"
                        ".startsWith('Comparison complete')"
                    )
                    assert mobile_page.evaluate(
                        "document.documentElement.scrollWidth <= window.innerWidth"
                    )
                    mobile.close()
                    browser.close()
                assert not errors, errors
                evidence = {
                    "data_mode": model["data_mode"],
                    "model_id": model["model_id"],
                    "runtime_source_identity_sha256": model["runtime_source_identity_sha256"],
                    "browser": "Chromium " + browser_version,
                    "checks": {
                        "saved_profile_seen_exclusion": True,
                        "ephemeral_likes_exclusion": True,
                        "genre_filter_ui": True,
                        "frozen_selection_disclosure": True,
                        "mobile_comparison_without_horizontal_overflow": True,
                        "no_javascript_errors": True,
                    },
                    "assets": {
                        path.name: {
                            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                            "bytes": path.stat().st_size,
                        }
                        for path in (output / "fixture-demo.png", output / "fixture-demo.webm")
                    },
                    "scope": "Real UI and HTTP; fictional fixture; recording has caption overlay",
                }
                (output / "verification.json").write_text(json.dumps(evidence, indent=2) + "\n")
                print(json.dumps(evidence, indent=2))
            finally:
                server.terminate()
                try:
                    server.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait(timeout=5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("docs/demo"))
    parser.add_argument("--channel", help="Optional installed browser channel, e.g. chrome")
    args = parser.parse_args()
    capture(args.output, args.channel)
