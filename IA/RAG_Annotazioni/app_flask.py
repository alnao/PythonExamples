from __future__ import annotations

from flask import Flask, jsonify, render_template, request

from rag_annotations.models import AnnotationIn
from rag_annotations.pipeline import Pipeline
from rag_annotations.llm.summarizer import build_summarizer

app = Flask(__name__)
pipeline = Pipeline()


def render_home(error: str | None = None, status: str | None = None, results=None, query: str = "", top_k: int = 5):
    return render_template(
        "home.html",
        error=error,
        status=status,
        results=results or [],
        query=query,
        top_k=top_k,
    )


def render_prompt_view(
    error: str | None = None,
    status: str | None = None,
    results=None,
    prompt: str = "",
    backend: str = "local",
    top_k: int = 5,
    summaries=None,
    summary_limit: int = 5,
):
    return render_template(
        "prompt_search.html",
        error=error,
        status=status,
        results=results or [],
        prompt=prompt,
        backend=backend,
        top_k=top_k,
        summaries=summaries or [],
        summary_limit=summary_limit,
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def ui_home():
    return render_home()


@app.get("/prompt-search")
def ui_prompt_home():
    return render_prompt_view()


@app.post("/ui/annotations")
def ui_create_annotation():
    text = (request.form.get("text", "") or "").strip()
    source = (request.form.get("source", "") or "").strip() or None
    if not text:
        return render_home(error="Testo obbligatorio per creare un'annotazione")
    count = pipeline.ingest([AnnotationIn(text=text, source=source)])
    return render_home(status=f"Annotazione salvata ({count} chunk)")


@app.post("/ui/search")
def ui_search():
    query = (request.form.get("query", "") or "").strip()
    raw_top_k = (request.form.get("top_k", "5") or "5").strip()
    try:
        top_k = max(1, min(50, int(raw_top_k)))
    except ValueError:
        top_k = 5
    if not query:
        return render_home(error="Inserisci un testo di ricerca", top_k=top_k)
    response = pipeline.search(query=query, top_k=top_k)
    return render_home(status="Ricerca completata", results=response.results, query=query, top_k=top_k)


@app.post("/ui/prompt-search")
def ui_prompt_search():
    prompt = (request.form.get("prompt", "") or "").strip()
    backend = (request.form.get("backend", "local") or "local").strip().lower()
    raw_top_k = (request.form.get("top_k", "5") or "5").strip()
    raw_summary_limit = (request.form.get("summary_limit", "5") or "5").strip()
    try:
        top_k = max(1, min(50, int(raw_top_k)))
    except ValueError:
        top_k = 5
    try:
        summary_limit = max(1, min(50, int(raw_summary_limit)))
    except ValueError:
        summary_limit = 5
    if not prompt:
        return render_prompt_view(error="Inserisci un prompt di ricerca", backend=backend, top_k=top_k, summary_limit=summary_limit)
    try:
        response = pipeline.search_with_backend(query=prompt, top_k=top_k, backend=backend)
        summarizer = build_summarizer(backend_override=backend)
        summaries = []
        ranked = sorted(response.results, key=lambda r: r.score)[:summary_limit]
        for item in ranked:
            abstract_en, abstract_it = summarizer.summarize(item.text)
            summaries.append(
                {
                    "chunk_id": item.chunk_id,
                    "annotation_id": item.annotation_id,
                    "abstract_en": abstract_en,
                    "abstract_it": abstract_it,
                }
            )
    except Exception as exc:
        return render_prompt_view(error=str(exc), backend=backend, prompt=prompt, top_k=top_k, summary_limit=summary_limit)
    return render_prompt_view(
        status="Ricerca completata",
        results=response.results,
        prompt=prompt,
        backend=backend,
        top_k=top_k,
        summaries=summaries,
        summary_limit=summary_limit,
    )


@app.post("/annotations")
def ingest_annotations():
    body = request.get_json(force=True, silent=True)
    if not body:
        return jsonify({"error": "No payload"}), 400
    if isinstance(body, dict):
        annotations = [AnnotationIn(**body)]
    elif isinstance(body, list):
        annotations = [AnnotationIn(**item) for item in body]
    else:
        return jsonify({"error": "Unsupported payload"}), 400
    count = pipeline.ingest(annotations)
    return jsonify({"ingested_chunks": count})


@app.get("/search")
def search():
    query = request.args.get("query")
    top_k = int(request.args.get("top_k", 5))
    if not query:
        return jsonify({"error": "query required"}), 400
    response = pipeline.search(query=query, top_k=top_k)
    return jsonify(response.model_dump())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
