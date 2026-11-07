"""The demo site: a small made-up recipe site the app serves at /demo/.

It lets someone try a crawl at once, without picking a real website or leaving this computer.
The dashboard's first-run screen starts a crawl of it in one click.
"""
from __future__ import annotations

from flask import Flask, Response, redirect, render_template

from demo.content import PAGES, ROBOTS_DISALLOW, ROOT, SITE_NAME, Block, Moved, Page, PlainText, at


def _not_found() -> Page:
    return Page(
        title="Page not found",
        blocks=[Block(paragraphs=["There is no recipe at this address. It may have been removed."])],
        status=404,
    )


def _serve(path: str):
    entry = PAGES.get(f"/{path}") or _not_found()
    if isinstance(entry, Moved):
        return redirect(entry.to, code=301)
    if isinstance(entry, PlainText):
        return Response(entry.text, mimetype="text/plain")
    return render_template("demo/page.html", page=entry, site_name=SITE_NAME, home=at("/")), entry.status


def _robots() -> Response:
    lines = ["# The demo site at /demo/ keeps its drafts out of crawls.", "User-agent: *"]
    lines += [f"Disallow: {path}" for path in ROBOTS_DISALLOW]
    return Response("\n".join(lines) + "\n", mimetype="text/plain")


def register(app: Flask) -> None:
    app.add_url_rule(f"{ROOT}/", "demo_home", _serve, defaults={"path": ""})
    app.add_url_rule(f"{ROOT}/<path:path>", "demo_page", _serve)
    app.add_url_rule("/robots.txt", "robots", _robots)
