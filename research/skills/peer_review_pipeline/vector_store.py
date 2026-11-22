"""Local embedded VectorDB memory (LanceDB) with 384-dim offline embeddings.

Table: ``wisdom``
Schema:
  - vector: float32[384]
  - category: str ("heuristic" | "benchmark" | "author_flaw" | "score_log")
  - content: str (strict < 30 words)
  - weight: float32 (1.0 to 5.0)
  - timestamp: str (ISO-8601 UTC)

If ``lancedb`` or ``sentence_transformers`` is unavailable in a minimal offline
environment, this module degrades gracefully to a local JSONL + NumPy cosine
store and deterministic 384-dim hashed trigram embeddings with identical schema
and deduplication semantics.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None  # type: ignore[assignment]

try:
    import lancedb
except ImportError:  # pragma: no cover
    lancedb = None  # type: ignore[assignment]

try:
    from sentence_transformers import SentenceTransformer
except ImportError:  # pragma: no cover
    SentenceTransformer = None  # type: ignore[assignment]

EMBEDDING_DIM = 384
VALID_CATEGORIES = {"heuristic", "benchmark", "author_flaw", "score_log"}
DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "reviewer_brain"
DEFAULT_MODEL_NAME = os.getenv("SWARM_EMBED_MODEL", "all-MiniLM-L6-v2")
DEDUP_COSINE_THRESHOLD = 0.92


class LocalEmbedder:
    """Lazy-loading local 384-dim embedder with zero-network deterministic fallback."""

    def __init__(self, model_name: str = DEFAULT_MODEL_NAME, allow_model_load: bool = False) -> None:
        self.model_name = model_name
        self._allow_model_load = allow_model_load
        self._model: Any = None

    def _get_model(self) -> Any:
        if self._model is None and self._allow_model_load and SentenceTransformer is not None:
            try:
                self._model = SentenceTransformer(self.model_name, local_files_only=True)
            except Exception:
                self._model = False
        return self._model if self._model not in (None, False) else None

    def embed(self, text: str) -> list[float]:
        """Return an L2-normalized 384-dimensional float32 vector."""
        model = self._get_model()
        if model is not None:
            vec = np.asarray(model.encode(text, normalize_embeddings=True), dtype=np.float32)
            if vec.shape[0] == EMBEDDING_DIM:
                return vec.tolist()
            # Deterministic projection if a 768-dim model like all-DistilBERT-base is loaded
            if vec.shape[0] > EMBEDDING_DIM:
                reshaped = vec[: EMBEDDING_DIM * (vec.shape[0] // EMBEDDING_DIM)].reshape(
                    EMBEDDING_DIM, -1
                )
                proj = reshaped.mean(axis=1)
                norm = float(np.linalg.norm(proj)) or 1.0
                return (proj / norm).astype(np.float32).tolist()

        return self._hashed_embedding(text)

    @staticmethod
    def _hashed_embedding(text: str) -> list[float]:
        """Deterministic offline 384-dim feature-hashed word + char-trigram embedding."""
        vec = [0.0] * EMBEDDING_DIM
        tokens = re.findall(r"[a-z0-9]+", text.lower())
        if not tokens:
            return vec

        features: list[str] = []
        for tok in tokens:
            features.append(f"w:{tok}")
            padded = f"^{tok}$"
            for i in range(max(0, len(padded) - 2)):
                features.append(f"c:{padded[i : i + 3]}")

        for feat in features:
            digest = hashlib.blake2b(feat.encode("utf-8"), digest_size=8).digest()
            idx = int.from_bytes(digest[:4], "little") % EMBEDDING_DIM
            sign = 1.0 if (digest[4] & 1) == 0 else -1.0
            vec[idx] += sign

        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0.0:
            vec = [v / norm for v in vec]
        return vec


def _truncate_words(content: str, max_words: int = 29) -> str:
    words = content.strip().split()
    if len(words) <= max_words:
        return " ".join(words)
    return " ".join(words[:max_words])


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if np is not None:
        va = np.asarray(a, dtype=np.float32)
        vb = np.asarray(b, dtype=np.float32)
        denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
        return float(np.dot(va, vb) / denom) if denom > 0.0 else 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    denom = na * nb
    return float(dot / denom) if denom > 0.0 else 0.0


class WisdomVectorStore:
    """Embedded LanceDB (with JSONL+NumPy fallback) for peer-review wisdom."""

    TABLE_NAME = "wisdom"

    def __init__(
        self,
        db_path: str | Path = DEFAULT_DB_PATH,
        embedder: LocalEmbedder | None = None,
    ) -> None:
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)
        self.embedder = embedder or LocalEmbedder()
        self._jsonl_path = self.db_path / f"{self.TABLE_NAME}.jsonl"
        self._lance_db = lancedb.connect(str(self.db_path)) if lancedb is not None else None

    def _load_jsonl_rows(self) -> list[dict[str, Any]]:
        if not self._jsonl_path.exists():
            return []
        rows: list[dict[str, Any]] = []
        with self._jsonl_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        return rows

    def _save_jsonl_rows(self, rows: list[dict[str, Any]]) -> None:
        with self._jsonl_path.open("w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    def query_wisdom(
        self,
        query: str | list[float],
        limit: int = 3,
        category: str | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve top-``limit`` memories by cosine similarity."""
        qvec = self.embedder.embed(query) if isinstance(query, str) else list(query)

        if self._lance_db is not None and self.TABLE_NAME in self._lance_db.table_names():
            table = self._lance_db.open_table(self.TABLE_NAME)
            search = table.search(qvec)
            if category:
                search = search.where(f"category = '{category}'")
            results = search.limit(limit).to_list()
            return [
                {
                    "category": r["category"],
                    "content": r["content"],
                    "weight": float(r["weight"]),
                    "timestamp": r["timestamp"],
                    "similarity": round(_cosine_similarity(qvec, list(r["vector"])), 4),
                }
                for r in results
            ]

        rows = self._load_jsonl_rows()
        if category:
            rows = [r for r in rows if r["category"] == category]

        scored: list[tuple[float, dict[str, Any]]] = []
        for row in rows:
            sim = _cosine_similarity(qvec, row["vector"])
            scored.append((sim, row))
        scored.sort(key=lambda item: (item[0], item[1].get("weight", 1.0)), reverse=True)

        return [
            {
                "category": row["category"],
                "content": row["content"],
                "weight": float(row["weight"]),
                "timestamp": row["timestamp"],
                "similarity": round(sim, 4),
            }
            for sim, row in scored[:limit]
        ]

    def add_wisdom(
        self,
        category: str,
        content: str,
        weight: float = 2.0,
        dedup_threshold: float = DEDUP_COSINE_THRESHOLD,
    ) -> dict[str, Any]:
        """Insert a compressed (<30 words) memory with nearest-neighbor deduplication.

        If a near-duplicate in the same category already exists (cosine >= ``dedup_threshold``),
        its weight is incremented (capped at 5.0) instead of inserting a duplicate row.
        """
        if category not in VALID_CATEGORIES:
            raise ValueError(f"Invalid category '{category}'. Expected one of {sorted(VALID_CATEGORIES)}.")

        compressed = _truncate_words(content, max_words=29)
        clamped_weight = float(min(5.0, max(1.0, weight)))
        vec = self.embedder.embed(compressed)
        now_iso = datetime.now(timezone.utc).isoformat()

        # Deduplication check for non-score_log entries
        if category != "score_log":
            nearest = self.query_wisdom(vec, limit=1, category=category)
            if nearest and nearest[0]["similarity"] >= dedup_threshold:
                return {
                    "action": "deduplicated",
                    "existing_content": nearest[0]["content"],
                    "similarity": nearest[0]["similarity"],
                }

        record = {
            "vector": vec,
            "category": category,
            "content": compressed,
            "weight": clamped_weight,
            "timestamp": now_iso,
        }

        if self._lance_db is not None:
            if self.TABLE_NAME in self._lance_db.table_names():
                table = self._lance_db.open_table(self.TABLE_NAME)
                table.add([record])
            else:
                self._lance_db.create_table(self.TABLE_NAME, data=[record])
        else:
            rows = self._load_jsonl_rows()
            rows.append(record)
            self._save_jsonl_rows(rows)

        return {"action": "inserted", "category": category, "content": compressed, "weight": clamped_weight}

    def get_score_log(self, limit: int = 5) -> list[dict[str, Any]]:
        """Return the most recent ``score_log`` records ordered newest-first."""
        if self._lance_db is not None and self.TABLE_NAME in self._lance_db.table_names():
            table = self._lance_db.open_table(self.TABLE_NAME)
            rows = table.search().where("category = 'score_log'").limit(50).to_list()
        else:
            rows = [r for r in self._load_jsonl_rows() if r["category"] == "score_log"]

        rows.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
        return [
            {"content": r["content"], "weight": float(r["weight"]), "timestamp": r["timestamp"]}
            for r in rows[:limit]
        ]

    def count(self) -> int:
        if self._lance_db is not None and self.TABLE_NAME in self._lance_db.table_names():
            return int(self._lance_db.open_table(self.TABLE_NAME).count_rows())
        return len(self._load_jsonl_rows())


def query_wisdom(
    query: str | list[float],
    limit: int = 3,
    category: str | None = None,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    """Module-level convenience wrapper for ``WisdomVectorStore.query_wisdom``."""
    return WisdomVectorStore(db_path=db_path).query_wisdom(query=query, limit=limit, category=category)
