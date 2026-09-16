import asyncio
from dataclasses import dataclass

from redisvl.utils.rerank import HFCrossEncoderReranker

from app.config import Settings


class RerankerError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class RerankerPreset:
    id: str
    display_name: str
    provider: str
    model: str


class RerankerProvider:
    """Timeout-bounded RedisVL cross-encoder provider for the demo pipeline."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client_tasks: dict[str, asyncio.Task[HFCrossEncoderReranker]] = {}
        self._presets = {
            "minilm_l6": RerankerPreset(
                id="minilm_l6",
                display_name="MiniLM L6 (balanced)",
                provider="local_hf",
                model=settings.reranker_model,
            ),
            "tinybert_l2": RerankerPreset(
                id="tinybert_l2",
                display_name="TinyBERT L2 (fast)",
                provider="local_hf",
                model="cross-encoder/ms-marco-TinyBERT-L-2-v2",
            ),
        }

    @property
    def presets(self) -> list[RerankerPreset]:
        if self._settings.reranker_provider == "none":
            return []
        return list(self._presets.values())

    def preset_for(self, reranker_id: str) -> RerankerPreset:
        if self._settings.reranker_provider == "none":
            raise RerankerError("reranker_disabled")
        preset = self._presets.get(reranker_id)
        if preset is None:
            raise RerankerError("reranker_unknown")
        return preset

    def is_ready(self, reranker_id: str) -> bool:
        """Whether the selected cross-encoder finished initializing before this request."""
        task = self._client_tasks.get(reranker_id)
        return (
            task is not None and task.done() and not task.cancelled() and task.exception() is None
        )

    async def rank(
        self, query: str, documents: list[dict[str, str]], reranker_id: str
    ) -> list[tuple[str, float]]:
        if self._settings.reranker_provider == "none":
            raise RerankerError("reranker_disabled")
        if self._settings.reranker_provider != "local_hf":
            raise RerankerError("reranker_provider_unavailable")
        preset = self.preset_for(reranker_id)

        timeout_seconds = self._settings.rerank_timeout_ms / 1_000
        try:
            reranker = await asyncio.wait_for(
                asyncio.shield(self._get_client(preset)), timeout=timeout_seconds
            )
            ranked_documents, scores = await asyncio.wait_for(
                asyncio.to_thread(
                    reranker.rank,
                    query,
                    documents,
                    limit=min(len(documents), self._settings.rerank_top_n),
                    return_score=True,
                ),
                timeout=timeout_seconds,
            )
        except TimeoutError as exc:
            raise RerankerError("reranker_timeout") from exc
        except Exception as exc:
            raise RerankerError("reranker_failed") from exc

        # RedisVL 0.20 returns ranked documents but preserves the original score order.
        # Sorting the score multiset restores alignment with the ranked document list.
        ranked_scores = sorted((float(score) for score in scores), reverse=True)
        return [
            (str(document["id"]), score)
            for document, score in zip(ranked_documents, ranked_scores, strict=True)
        ]

    async def _get_client(self, preset: RerankerPreset) -> HFCrossEncoderReranker:
        task = self._client_tasks.get(preset.id)
        if task is None:
            task = asyncio.create_task(asyncio.to_thread(self._build_client, preset))
            self._client_tasks[preset.id] = task
        return await task

    def _build_client(self, preset: RerankerPreset) -> HFCrossEncoderReranker:
        return HFCrossEncoderReranker(
            model=preset.model,
            limit=self._settings.rerank_top_n,
            return_score=True,
        )
