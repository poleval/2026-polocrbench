#!/usr/bin/env python3
"""Local, read-only PDF dataset explorer. Run: python3 scripts/explore_dataset.py."""
import argparse
import csv
from functools import lru_cache
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

import pymupdf
from polocrbench.annotation import AnnotationAction, AnnotationStore

def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def load_documents(DATA):
    metadata = {Path(urlsplit(r["dokument_url"]).path).name: r
                for r in read_csv(DATA / "dane/teksty-indeks.csv")}
    measurements = {r["path"]: r for r in map(json.loads, (DATA / "classification/pdf-measurements.jsonl").read_text().splitlines())}
    docs = []
    for row in read_csv(DATA / "classification/pdf-classification.csv"):
        name = Path(row["path"]).name
        meta = metadata.get(name, {})
        text_name = Path(urlsplit(meta.get("tekst_url", "")).path).name
        text_path = DATA / "extracted/teksty/teksty" / text_name
        docs.append({
            "id": Path(name).stem, "filename": name, "path": row["path"],
            "sha256": measurements[row["path"]]["sha256"],
            "label": row.get("final_classification", row["classification"]),
            "confidence": float(row.get("final_confidence", row["confidence"])),
            "pages": int(row["pages"]), "scan_pages": int(row["raster_pages"]),
            "ocr_needed": int(row["scan_pages_needing_ocr"]),
            "ocr_pages": int(row["scan_pages_with_text_layer"]),
            "organization": meta.get("organ", ""), "date": meta.get("data", ""),
            "title": meta.get("opis", "") or name, "topic": meta.get("temat", ""),
            "text_source": meta.get("zrodlo_tekstu", ""),
            "text_path": str(text_path.relative_to(DATA)) if text_path.is_file() else None,
            "page_metrics": measurements[row["path"]]["page_measurements"],
        })
    return docs


@lru_cache(maxsize=48)
def page_image(path, page_number, scale):
    with pymupdf.open(path) as doc:
        return doc[page_number - 1].get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False).tobytes("png")


def handler_for(docs, DATA, UI, ANNOTATION_ROOT):
    by_id = {d["id"]: d for d in docs}
    store = AnnotationStore(ANNOTATION_ROOT / "annotations")

    def sample(query):
        doc = by_id.get(query.get("id", [""])[0])
        page = int(query.get("page", ["1"])[0])
        if not doc or not 1 <= page <= doc["pages"]:
            raise ValueError("Nieznany dokument lub strona.")
        return doc, page, f"gm_{doc['sha256'][:16]}_p{page:04d}"

    class Handler(BaseHTTPRequestHandler):
        def send(self, body, content_type, status=200):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            url = urlsplit(self.path)
            query = parse_qs(url.query)
            try:
                if url.path == "/api/documents":
                    return self.send(json.dumps(docs, ensure_ascii=False).encode(), "application/json; charset=utf-8")
                if url.path == "/api/queue":
                    queue_path = ANNOTATION_ROOT / "annotation-queue.jsonl"
                    rows = []
                    if queue_path.exists():
                        for line in queue_path.read_text().splitlines():
                            row = json.loads(line)
                            record = store.get(row["id"])
                            rows.append({key: row[key] for key in ("id", "document_id", "page", "planned_split", "group_id")})
                            rows[-1].update(status=record["status"], reviews=len(record["reviews"]))
                    return self.send(json.dumps(rows).encode(), "application/json")
                if url.path == "/api/annotation":
                    doc, page, sample_id = sample(query)
                    row = store.get(sample_id)
                    with pymupdf.open(DATA / doc["path"]) as pdf:
                        row["preannotation"] = pdf[page - 1].get_text(sort=True)
                    return self.send(json.dumps(row, ensure_ascii=False).encode(), "application/json; charset=utf-8")
                if url.path in ("/api/page", "/api/text"):
                    doc = by_id.get(query.get("id", [""])[0])
                    if not doc:
                        return self.send(b"Unknown document", "text/plain", 404)
                    page = int(query.get("page", ["1"])[0])
                    if not 1 <= page <= doc["pages"]:
                        return self.send(b"Invalid page", "text/plain", 400)
                    if url.path == "/api/page":
                        scale = min(2, max(.4, float(query.get("scale", ["1.3"])[0])))
                        return self.send(page_image(str(DATA / doc["path"]), page, scale), "image/png")
                    if query.get("source", [""])[0] == "publisher":
                        text = (DATA / doc["text_path"]).read_text(errors="replace") if doc["text_path"] else "Brak dostarczonego tekstu."
                    else:
                        with pymupdf.open(DATA / doc["path"]) as pdf:
                            text = pdf[page - 1].get_text(sort=True)
                    return self.send(json.dumps({"text": text}, ensure_ascii=False).encode(), "application/json; charset=utf-8")
                if url.path.startswith("/files/"):
                    path = (DATA / unquote(url.path.removeprefix("/files/"))).resolve()
                    if not path.is_relative_to((DATA / "dokumenty").resolve()) or not path.is_file():
                        return self.send(b"Not found", "text/plain", 404)
                    return self.send(path.read_bytes(), mimetypes.guess_type(path.name)[0] or "application/octet-stream")
                path = UI / ("index.html" if url.path == "/" else unquote(url.path).lstrip("/"))
                if not path.resolve().is_relative_to(UI.resolve()) or not path.is_file():
                    return self.send(b"Not found", "text/plain", 404)
                return self.send(path.read_bytes(), mimetypes.guess_type(path.name)[0] or "application/octet-stream")
            except (ValueError, KeyError):
                self.send(b"Invalid request", "text/plain", 400)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def do_POST(self):
            url = urlsplit(self.path)
            if url.path != "/api/annotation":
                return self.send(b"Not found", "text/plain", 404)
            origin = self.headers.get("Origin")
            if origin and origin != "http://" + self.headers.get("Host", ""):
                return self.send(b"Cross-origin write denied", "text/plain", 403)
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length < 1 or length > 2_000_000:
                    raise ValueError("Anotacja musi mieścić się w 2 MB.")
                if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                    raise ValueError("Wymagany Content-Type application/json.")
                doc, page, sample_id = sample(parse_qs(url.query))
                action = AnnotationAction.model_validate_json(self.rfile.read(length))
                row = store.update(sample_id, action)
                return self.send(json.dumps(row, ensure_ascii=False).encode(), "application/json; charset=utf-8")
            except ValueError as exc:
                return self.send(json.dumps({"error": str(exc)}, ensure_ascii=False).encode(), "application/json; charset=utf-8", 400)

    return Handler


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8941)
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--ui", type=Path, default=Path(__file__).resolve().parent / "static")
    args = parser.parse_args()
    data = args.workspace / "glos-migranta"
    private = args.workspace / "benchmark/2026-polocrbench-secret/workspace"
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler_for(load_documents(data), data, args.ui, private))
    print(f"Explorer: http://127.0.0.1:{server.server_address[1]}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()


if __name__ == "__main__":
    main()
