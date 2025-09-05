import httpx
import json
import re
from dataclasses import dataclass, asdict
from typing import ClassVar, Any
from datetime import datetime, timedelta
import hashlib

from tenacity import retry, stop_after_attempt, wait_exponential, RetryError

from ..config import settings
from ..llm.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from ..utils.logging import logger
from ..utils.redis_client import get_redis
from ..services.rate_limit import enforce_rate_limit

try:
     logger = logger.bind(module="app.services.llm")  # si tu logger soporta .bind()
except Exception:
     pass

@dataclass
class NegotiationMessage:
    channel: str
    subject: str | None
    message: str
    strategy: str
    new_amount_suggestion: float
    target_pct: float
    confidence: float
    risks: list[str]
    meta: dict[str, Any]

class LlmClient:
    """Abstract base class for LLM clients."""
    async def generate_negotiation_message(
        self,
        provider: str,
        amount: float,
        period: str,
        user_id: int,
        target_pct: float = 0.20,
        locale: str = "es_AR",
        channel: str | None = None,
        context: dict | None = None
    ) -> NegotiationMessage:
        raise NotImplementedError

class OpenAiClient(LlmClient):
    """Client for OpenAI's API with caching, circuit breaker, and fallback."""

    API_URL: ClassVar[str] = "https://api.openai.com/v1/chat/completions"
    CIRCUIT_BREAKER_THRESHOLD: ClassVar[int] = 3
    CIRCUIT_BREAKER_PERIOD_MIN: ClassVar[int] = 5
    CIRCUIT_BREAKER_COOLDOWN_MIN: ClassVar[int] = 2

    def __init__(self, http_client: httpx.AsyncClient):
        self.http_client = http_client
        self.redis = get_redis()
        self._failures = []
        self._circuit_open_until = None

    def _check_circuit_breaker(self) -> bool:
        """Checks if the circuit breaker is open, returns True if open."""
        if self._circuit_open_until and datetime.now() < self._circuit_open_until:
            logger.warning("llm.circuit_breaker.open", open_until=self._circuit_open_until.isoformat())
            return True

        now = datetime.now()
        self._failures = [t for t in self._failures if now - t < timedelta(minutes=self.CIRCUIT_BREAKER_PERIOD_MIN)]

        if len(self._failures) >= self.CIRCUIT_BREAKER_THRESHOLD:
            self._circuit_open_until = now + timedelta(minutes=self.CIRCUIT_BREAKER_COOLDOWN_MIN)
            logger.error("llm.circuit_breaker.tripped", failures=len(self._failures), cooldown_min=self.CIRCUIT_BREAKER_COOLDOWN_MIN)
            return True

        return False

    def _record_failure(self):
        self._failures.append(datetime.now())

    def _record_success(self):
        self._failures = []
        self._circuit_open_until = None

    def _sanitize_input(self, text: str) -> str:
        """Removes control characters and excessive whitespace."""
        return re.sub(r"[\x00-\x1f\x7f-\x9f]|\s+", " ", text).strip()

    def _generate_fallback_message(
        self,
        provider: str,
        amount: float,
        period: str,
        target_pct: float,
        channel: str,
        reason: str = "fallback"
    ) -> NegotiationMessage:
        logger.info(event=f"llm.fallback", reason=reason, provider=provider)
        new_amount = amount * (1 - target_pct)
        discount_pct_str = f"{target_pct:.0%}"

        if channel == "phone_script":
            subject = "Guion de llamada de negociación"
            message_body = (
                f"- Saludar y presentarse como titular del servicio de {provider}.\n"
                f"- Mencionar la factura del período {period} por un monto de ${amount:,.2f}.\n"
                f"- Solicitar un descuento del {discount_pct_str} para mantener el servicio.\n"
                f"- Proponer un nuevo monto final de aproximadamente ${new_amount:,.2f}.\n"
                f"- Agradecer y quedar a la espera de una respuesta."
            )
        else:
            subject = f"Consulta sobre mi factura de {provider}"
            message_body = (
                f"Estimados, les escribo en referencia a mi última factura del período {period} por un total de ${amount:,.2f}. "
                f"Me gustaría solicitar una bonificación del {discount_pct_str} para continuar con el servicio. "
                f"Un monto ajustado a ${new_amount:,.2f} sería más adecuado. "
                f"Agradezco su tiempo y quedo a la espera de su confirmación. Saludos cordiales."
            )

        return NegotiationMessage(
            channel=channel,
            subject=subject if channel == "email" else None,
            message=message_body[:700],
            strategy="retention",
            new_amount_suggestion=round(new_amount, 2),
            target_pct=target_pct,
            confidence=0.3,
            risks=["El proveedor puede no aceptar la propuesta sin más contexto."],
            meta={"provider": "fallback", "model": f"template-v1-{reason}", "cache_hit": False},
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def _call_openai_api(self, payload: dict) -> dict:
        """Makes a single, retryable API call to OpenAI."""
        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        response = await self.http_client.post(
            self.API_URL,
            json=payload,
            headers=headers,
            timeout=settings.llm_timeout_s,
        )
        response.raise_for_status()
        return response.json()

    async def generate_negotiation_message(
        self,
        provider: str,
        amount: float,
        period: str,
        user_id: int,
        target_pct: float = 0.20,
        locale: str = "es_AR",
        channel: str | None = "email",
        context: dict | None = None
    ) -> NegotiationMessage:
        channel = channel or "email"

        await enforce_rate_limit(f"llm:user:{user_id}", ttl_seconds=60, max_requests=5)

        cache_key_raw = f"{provider}:{period}:{amount}:{target_pct}:{locale}:{channel}"
        cache_key = f"llm:neg_msg:{hashlib.md5(cache_key_raw.encode()).hexdigest()}"

        cached_result = await self.redis.get(cache_key)
        if cached_result:
            logger.info("llm.cache.hit", key=cache_key)
            data = json.loads(cached_result)
            data["meta"]["cache_hit"] = True
            return NegotiationMessage(**data)
        logger.info("llm.cache.miss", key=cache_key)

        if self._check_circuit_breaker():
            return self._generate_fallback_message(provider, amount, period, target_pct, channel, reason="circuit_open")

        if not settings.llm_enable or not settings.openai_api_key:
            return self._generate_fallback_message(provider, amount, period, target_pct, channel, reason="disabled")

        sanitized_provider = self._sanitize_input(provider)
        sanitized_period = self._sanitize_input(period)

        user_prompt = USER_PROMPT_TEMPLATE.format(
            provider=sanitized_provider,
            amount=amount,
            period=sanitized_period,
            target_pct=target_pct,
            channel=channel,
            locale=locale,
            context=json.dumps(context, indent=2, ensure_ascii=False) if context else "No hay contexto adicional."
        )

        payload = {
            "model": settings.llm_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": settings.llm_temperature,
            "max_tokens": settings.llm_max_tokens,
            "response_format": {"type": "json_object"},
        }

        try:
            if settings.llm_dry_run:
                logger.info(event="llm.dry_run", payload_meta={k: v for k, v in payload.items() if k != 'messages'})
                raise ValueError("Dry run enabled, skipping API call.")

            api_response = await self._call_openai_api(payload)
            content = api_response["choices"][0]["message"]["content"]
            llm_data = json.loads(content)

            if not all(k in llm_data for k in asdict(NegotiationMessage("",None,"","",0.0,0.0,0.0,[],{}))):
                raise ValueError("LLM response missing required keys")

            llm_data["meta"] = {
                "provider": "openai", "model": api_response.get("model"),
                "tokens_prompt": api_response["usage"]["prompt_tokens"],
                "tokens_completion": api_response["usage"]["completion_tokens"],
                "total_tokens": api_response["usage"]["total_tokens"],
                "cache_hit": False,
            }

            result_message = NegotiationMessage(**llm_data)
            await self.redis.set(cache_key, json.dumps(asdict(result_message)), ex=settings.llm_cache_ttl_s)

            self._record_success()
            return result_message

        except (httpx.HTTPStatusError, httpx.RequestError, RetryError, json.JSONDecodeError, ValueError, KeyError) as e:
            self._record_failure()
            logger.error(
                event="llm.error", error_type=type(e).__name__, error_message=str(e),
                provider=provider, fallback_used=True,
            )
            return self._generate_fallback_message(provider, amount, period, target_pct, channel, reason="api_error")
