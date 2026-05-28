import asyncio
import logging
import os
import re
import time

import httpx  # pyright: ignore[reportMissingImports]

logger = logging.getLogger(__name__)

OPENROUTER_DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_DEFAULT_PRIMARY_MODEL = "qwen/qwen3-next-80b-a3b-instruct:free"
OPENROUTER_DEFAULT_FALLBACK_MODEL = "z-ai/glm-4.5-air:free"


def _clean_text(text: str | None) -> str:
    if not text:
        return ""
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:\w+)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = cleaned.strip().strip('"').strip()
    return cleaned


async def _call_model(messages, model: str, temperature: float, max_tokens: int, timeout: float):
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY não configurada.")

    base_url = os.getenv("OPENROUTER_BASE_URL", OPENROUTER_DEFAULT_BASE_URL).rstrip("/")
    site_url = os.getenv("OPENROUTER_SITE_URL", "http://localhost:5173")
    app_name = os.getenv("OPENROUTER_APP_NAME", "Deadly Truth")
    started_at = time.perf_counter()

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": site_url,
                "X-Title": app_name,
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )
        response.raise_for_status()
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        data = response.json()
        text = _clean_text(data.get("choices", [{}])[0].get("message", {}).get("content"))
        return text, elapsed_ms


async def call_openrouter(messages, temperature=0.85, max_tokens=220, timeout=10):
    """
    Chama primeiro o modelo principal.
    Se falhar, der timeout ou retornar vazio, chama o modelo fallback.
    Se ambos falharem, retorna None para permitir fallback local.
    """
    configured_timeout = float(os.getenv("AI_TIMEOUT_SECONDS", timeout or 10))
    primary_model = os.getenv("OPENROUTER_PRIMARY_MODEL", OPENROUTER_DEFAULT_PRIMARY_MODEL)
    fallback_model = os.getenv("OPENROUTER_FALLBACK_MODEL", OPENROUTER_DEFAULT_FALLBACK_MODEL)

    attempts = [
        ("primary", primary_model, f"[OPENROUTER] Tentando modelo principal: {primary_model}"),
        ("fallback", fallback_model, f"[OPENROUTER] Falha no modelo principal, tentando fallback: {fallback_model}"),
    ]

    last_error = None
    for role, model, start_log in attempts:
        logger.info(start_log)
        try:
            text, elapsed_ms = await asyncio.wait_for(
                _call_model(messages, model, temperature, max_tokens, configured_timeout),
                timeout=configured_timeout + 1,
            )
            if text:
                if role == "primary":
                    logger.info(f"[OPENROUTER] Sucesso com modelo principal model={model} elapsed_ms={elapsed_ms}")
                else:
                    logger.info(f"[OPENROUTER] Sucesso com fallback model={model} elapsed_ms={elapsed_ms}")
                call_openrouter.last_result = {
                    "source": "openrouter" if role == "primary" else "fallback_model",
                    "model": model,
                    "elapsed_ms": elapsed_ms,
                }
                return text
            last_error = "resposta vazia"
            logger.warning(f"[OPENROUTER] Modelo {model} retornou vazio elapsed_ms={elapsed_ms}")
        except Exception as exc:
            last_error = str(exc)
            logger.warning(f"[OPENROUTER] Erro no modelo {model}: {exc}")

    logger.warning(f"[OPENROUTER] Ambos os modelos falharam, usando fallback local reason={last_error}")
    call_openrouter.last_result = {
        "source": "local_fallback",
        "model": None,
        "error": last_error,
    }
    return None


call_openrouter.last_result = {"source": None, "model": None}
