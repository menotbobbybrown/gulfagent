"""
T38 — Arabic message detection → route to Qwen3 via Ollama.

Detection: fast Unicode range check (no external dep required).
Routing: if Arabic detected, use Ollama/Qwen3; else use Claude.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime

import httpx

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Arabic Unicode block: U+0600–U+06FF (core Arabic)
# Also catches Arabic Presentation Forms A/B, Arabic Supplement, etc.
_ARABIC_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]")

# Threshold: if ≥15% of non-whitespace chars are Arabic script → Arabic
ARABIC_THRESHOLD = 0.15


def detect_arabic(text: str) -> bool:
    """Return True if the text is predominantly Arabic script."""
    clean = text.replace(" ", "").replace("\n", "")
    if not clean:
        return False
    arabic_chars = len(_ARABIC_RE.findall(clean))
    ratio = arabic_chars / len(clean)
    return ratio >= ARABIC_THRESHOLD


async def run_ollama(
    prompt: str,
    system_prompt: str = "",
    model: str | None = None,
) -> tuple[str, int]:
    """
    Call Ollama with the configured Arabic LLM.
    Returns (response_text, estimated_tokens).
    Falls back to empty string on error so caller can handle.
    """
    model = model or settings.ollama_model
    base_url = settings.ollama_base_url.rstrip("/")

    payload: dict = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.3, "num_predict": 2048},
    }
    if system_prompt:
        payload["system"] = system_prompt

    try:
        start_time = datetime.now()
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{base_url}/api/generate", json=payload)
            resp.raise_for_status()
            data = resp.json()
            end_time = datetime.now()
            latency = (end_time - start_time).total_seconds()
            
            text = data.get("response", "")
            # Ollama returns eval_count (output tokens) + prompt_eval_count
            tokens = data.get("eval_count", 0) + data.get("prompt_eval_count", 0)
            
            logger.info(
                "Ollama success: model=%s, tokens=%d, latency=%.2fs", 
                model, tokens, latency
            )
            return text, tokens
    except httpx.ConnectError:
        logger.warning("Ollama not reachable at %s — falling back to Claude", base_url)
        return "", 0
    except Exception as e:
        logger.error("Ollama error: %s", e)
        return "", 0


GULF_AGENT_SYSTEM_AR = (
    "أنت GulfAgent، مساعد ذكاء اصطناعي خبير ومتخصص في خدمة الشركات والمؤسسات في دول مجلس التعاون الخليجي (الإمارات، السعودية، قطر، الكويت، البحرين، عمان). "
    "تساعد في أتمتة المهام، صياغة الخطابات الرسمية، تحليل البيانات، وتقديم المشورة التجارية المتوافقة مع العادات والقوانين المحلية في المنطقة. "
    "يجب أن تكون إجاباتك مهنية، دقيقة، وباللغة العربية الفصحى (أو اللهجة البيضاء الخليجية إذا كان ذلك مناسباً للسياق). "
    "تجنب الإطالة غير الضرورية وركز على الحلول العملية."
)


GULF_AGENT_SYSTEM_EN = (
    "You are GulfAgent, an AI assistant specialised in helping GCC businesses "
    "with tasks including research, analysis, scheduling, communication drafts, "
    "and regional business operations. Be concise and actionable. "
    "Respond in the same language as the user's prompt."
)


async def route_to_llm(prompt: str) -> tuple[str, int, str]:
    """
    Detect language and route to the appropriate LLM.
    Returns (result_text, tokens_used, model_used).

    Arabic  → Ollama/Qwen3 (with Claude fallback if Ollama unreachable)
    English → Claude claude-sonnet-4-20250514
    """
    is_arabic = detect_arabic(prompt)

    if is_arabic:
        text, tokens = await run_ollama(prompt, system_prompt=GULF_AGENT_SYSTEM_AR)
        if text:
            logger.info("Arabic prompt routed to Ollama (%s)", settings.ollama_model)
            return text, tokens, f"ollama/{settings.ollama_model}"
        # Ollama unavailable → fall through to Claude
        logger.warning("Ollama unavailable, falling back to Claude for Arabic prompt")

    # Claude path
    import anthropic
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    system = GULF_AGENT_SYSTEM_AR if is_arabic else GULF_AGENT_SYSTEM_EN

    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    content = response.content[0].text if response.content else ""
    tokens = response.usage.input_tokens + response.usage.output_tokens
    return content, tokens, "claude-sonnet-4-20250514"
