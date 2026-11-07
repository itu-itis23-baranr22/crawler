"""The web app: pages and the JSON API. Run with: python app.py"""
from __future__ import annotations

from urllib.parse import urlsplit

from flask import Flask, jsonify, render_template, request

import config
from crawler.crawler_manager import crawler_manager
from services.crawler_service import crawler_service
from services.search_service import search_service
from storage.database import db


def _number(name: str, default: int) -> int:
    try:
        return int(request.args.get(name, default))
    except (TypeError, ValueError):
        return default


def create_app() -> Flask:
    app = Flask(__name__)
    crawler_manager.recover()

    @app.before_request
    def only_this_machine():
        """Stop websites open in the browser from reaching this API.

        The Host check blocks DNS rebinding. The Origin check blocks cross-site writes,
        which browsers would otherwise send without asking when they look like plain forms.
        """
        if request.host.rsplit(":", 1)[0].strip("[]") not in config.ALLOWED_HOSTS:
            return jsonify(message="This server only answers on the local machine."), 403
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            origin = request.headers.get("Origin")
            if origin and urlsplit(origin).netloc != request.host:
                return jsonify(message="Requests from other websites are not allowed."), 403
        return None

    @app.teardown_request
    def close_database(_exception):
        db.close_thread_connection()

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify(message="Not found."), 404

    @app.errorhandler(405)
    def wrong_method(_error):
        return jsonify(message="Method not allowed."), 405

    # ---------- Pages ----------
    @app.route("/")
    def home():
        return render_template("index.html", active="crawls")

    @app.route("/search-page")
    def search_page():
        return render_template("search.html", active="search")

    @app.route("/crawler/<crawler_id>")
    def crawler_status_page(crawler_id):
        return render_template("crawler_status.html", crawler_id=crawler_id, active="crawls")

    # ---------- Crawler API ----------
    @app.route("/api/crawlers", methods=["POST"])
    def create_crawler():
        data = request.get_json(silent=True)
        if data is None and request.mimetype != "application/json":
            return jsonify(message="Send the request as application/json."), 415
        result, status_code = crawler_service.create_crawler(data)
        return jsonify(result), status_code

    @app.route("/api/crawlers", methods=["GET"])
    def list_crawlers():
        result, status_code = crawler_service.list_crawlers()
        return jsonify(result), status_code

    @app.route("/api/crawlers/<crawler_id>", methods=["GET"])
    def get_crawler_status(crawler_id):
        result, status_code = crawler_service.get_crawler_status(crawler_id)
        return jsonify(result), status_code

    @app.route("/api/crawlers/<crawler_id>/wait-status", methods=["GET"])
    def wait_crawler_status(crawler_id):
        result, status_code = crawler_service.wait_for_crawler_status(
            crawler_id=crawler_id,
            since_version=_number("since_version", 0),
            timeout=_number("timeout", 20),
        )
        return jsonify(result), status_code

    @app.route("/api/crawlers/<crawler_id>/pause", methods=["POST"])
    def pause_crawler(crawler_id):
        result, status_code = crawler_service.pause_crawler(crawler_id)
        return jsonify(result), status_code

    @app.route("/api/crawlers/<crawler_id>/resume", methods=["POST"])
    def resume_crawler(crawler_id):
        result, status_code = crawler_service.resume_crawler(crawler_id)
        return jsonify(result), status_code

    @app.route("/api/crawlers/<crawler_id>/stop", methods=["POST"])
    def stop_crawler(crawler_id):
        result, status_code = crawler_service.stop_crawler(crawler_id)
        return jsonify(result), status_code

    @app.route("/api/crawlers/<crawler_id>/restart", methods=["POST"])
    def restart_crawler(crawler_id):
        result, status_code = crawler_service.restart_crawler(crawler_id)
        return jsonify(result), status_code

    @app.route("/api/crawlers/<crawler_id>/logs", methods=["GET"])
    def get_crawler_logs(crawler_id):
        result, status_code = crawler_service.get_crawler_logs(crawler_id, last_n=_number("last_n", 200))
        return jsonify(result), status_code

    @app.route("/api/crawlers/<crawler_id>/visits", methods=["GET"])
    def get_crawler_visits(crawler_id):
        result, status_code = crawler_service.get_crawler_visits(crawler_id, after=_number("after", 0))
        return jsonify(result), status_code

    # ---------- Search API ----------
    @app.route("/search", methods=["GET"])
    def search():
        result, status_code = search_service.search(
            query=request.args.get("query", ""),
            sort_by=request.args.get("sortBy", "relevance"),
            page=request.args.get("page", 1),
            page_size=request.args.get("page_size", 10),
        )
        return jsonify(result), status_code

    @app.route("/lucky", methods=["GET"])
    def lucky():
        result, status_code = search_service.lucky(page_size=request.args.get("page_size", 10))
        return jsonify(result), status_code

    @app.route("/api/stats", methods=["GET"])
    def stats():
        result, status_code = search_service.stats()
        return jsonify(result), status_code

    return app


if __name__ == "__main__":
    print(f"Crawler is running at http://{config.HOST}:{config.PORT}  (press Ctrl+C to stop)")
    create_app().run(host=config.HOST, port=config.PORT, threaded=True, debug=False)
