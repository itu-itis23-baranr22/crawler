# app.py

from flask import Flask, render_template, jsonify, request

from services.crawler_service import crawler_service
from services.search_service import search_service


def create_app() -> Flask:
    app = Flask(__name__)

    # ---------- Pages ----------
    @app.route("/")
    def home():
        return render_template("index.html")

    @app.route("/search")
    def search_page():
        return render_template("search.html")

    @app.route("/crawler/<crawler_id>")
    def crawler_status_page(crawler_id):
        return render_template("crawler_status.html", crawler_id=crawler_id)

    # ---------- Crawler API ----------
    @app.route("/api/crawlers", methods=["POST"])
    def create_crawler():
        data = request.get_json(force=True)
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
        since_version = request.args.get("since_version", 0)
        timeout = request.args.get("timeout", 20)

        try:
            since_version = int(since_version)
        except (ValueError, TypeError):
            since_version = 0

        try:
            timeout = int(timeout)
        except (ValueError, TypeError):
            timeout = 20

        result, status_code = crawler_service.wait_for_crawler_status(
            crawler_id=crawler_id,
            since_version=since_version,
            timeout=timeout,
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
        last_n = request.args.get("last_n", 200)
        try:
            last_n = int(last_n)
        except (ValueError, TypeError):
            last_n = 200

        result, status_code = crawler_service.get_crawler_logs(crawler_id, last_n=last_n)
        return jsonify(result), status_code

    # ---------- Search API ----------
    @app.route("/api/search", methods=["GET"])
    def search():
        query = request.args.get("query", "").strip()
        page = request.args.get("page", 1)
        page_size = request.args.get("page_size", 10)
        result, status_code = search_service.search(query=query, page=page, page_size=page_size)
        return jsonify(result), status_code

    @app.route("/api/search/assignment", methods=["GET"])
    def search_assignment():
        query = request.args.get("query", "").strip()
        page = request.args.get("page", 1)
        page_size = request.args.get("page_size", 10)
        result, status_code = search_service.search_assignment_format(
            query=query, page=page, page_size=page_size
        )
        return jsonify(result), status_code

    @app.route("/api/lucky", methods=["GET"])
    def lucky():
        page_size = request.args.get("page_size", 10)
        result, status_code = search_service.lucky(page_size=page_size)
        return jsonify(result), status_code

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)