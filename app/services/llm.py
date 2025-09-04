from dataclasses import dataclass
from ..config import settings

@dataclass
class NegotiationMessage:
    message: str

class LlmClient:
    async def generate_negotiation_message(self, provider: str, amount: float, period: str, target_pct: float = 0.2) -> NegotiationMessage:
        raise NotImplementedError

class OpenAiClient(LlmClient):
    async def generate_negotiation_message(self, provider: str, amount: float, period: str, target_pct: float = 0.2) -> NegotiationMessage:
        if not settings.openai_api_key:
            # Mocked response
            discount = int(target_pct * 100)
            msg = (f"Hola, soy el titular del servicio. En la factura {period} el cargo fue de ARS {amount:.2f}. "
                   f"Me gustaría evaluar una mejora de {discount}% por permanencia. "
                   "Quedo a disposición para confirmar el ajuste. Gracias.")
            return NegotiationMessage(message=msg)
        # TODO: Implement real OpenAI API call with safe prompt
        discount = int(target_pct * 100)
        return NegotiationMessage(message=f"(LLM) Solicitud de mejora de {discount}% para {provider} sobre período {period}.")
