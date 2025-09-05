# Patch Notes: LLM Negotiation Suite

## 1. Visión General

Esta actualización introduce una suite de negociación asistida por LLM para mejorar la capacidad del sistema de conseguir ahorros para los usuarios. Incluye un nuevo cliente LLM (OpenAI), prompts especializados, lógica de fallback determinista, y nuevos endpoints para interactuar con los mensajes generados.

## 2. Variables de Entorno Nuevas

Añada las siguientes variables a su fichero `.env` para configurar el servicio LLM:

```bash
# Activa o desactiva globalmente la funcionalidad LLM
LLM_ENABLE=true

# Proveedor de LLM a utilizar (actualmente solo "openai")
LLM_PROVIDER="openai"

# Modelo específico de OpenAI a utilizar
LLM_MODEL="gpt-4.1-mini"

# API Key de OpenAI
OPENAI_API_KEY="sk-..."

# Timeout en segundos para las llamadas a la API del LLM
LLM_TIMEOUT_S=20

# Máximo de tokens a generar en la respuesta
LLM_MAX_TOKENS=500

# Temperatura de la generación (creatividad vs. determinismo)
LLM_TEMPERATURE=0.4

# Idioma para la generación de mensajes
LLM_LANG="es_AR"

# TTL en segundos para el cache de respuestas del LLM
LLM_CACHE_TTL_S=3600

# Si es 'true', no se llama a la API del LLM, solo se loguea el intento.
LLM_DRY_RUN=false
```

## 3. Nuevos Endpoints

### Iniciar una Negociación (Actualizado)

El endpoint existente ahora invoca al LLM para generar el mensaje inicial.

**Request:**
```bash
curl -X POST "http://localhost:8000/services/1/negotiate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"target_pct": 0.25}'
```

**Respuesta (Actualizada):**
La respuesta ahora incluye campos de previsualización del LLM.
```json
{
  "id": 1,
  "status": "proposed",
  "strategy": "retention",
  "initial_amount": 10000.0,
  "new_amount": null,
  "transcript_json": null,
  "llm_channel": "email",
  "llm_message_preview": "Estimados, les escribo en referencia a mi última factura...",
  "llm_new_amount_suggestion": 7500.0,
  "llm_confidence": 0.65
}
```

### Obtener Mensaje LLM Completo

Recupera el contenido completo generado por el LLM para una negociación.

**Request:**
```bash
curl -X GET "http://localhost:8000/negotiations/1/llm-message" \
  -H "Authorization: Bearer $TOKEN"
```

**Respuesta:**
```json
{
  "channel": "email",
  "subject": "Consulta sobre mi factura de Movistar",
  "message": "Estimados, les escribo en referencia a mi última factura...",
  "strategy": "retention",
  "new_amount_suggestion": 7500.0,
  "target_pct": 0.25,
  "confidence": 0.65,
  "risks": ["El proveedor puede requerir una llamada para confirmar."]
}
```

### Regenerar Mensaje LLM (Admin)

Permite a un administrador forzar la regeneración de un mensaje con parámetros opcionales.

**Request:**
```bash
curl -X POST "http://localhost:8000/negotiations/1/llm-regenerate" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"target_pct": 0.30, "channel": "phone_script"}'
```

**Respuesta:**
Devuelve el nuevo mensaje generado.

### Estado del Servicio LLM (Admin)

Devuelve la configuración y estado actual del servicio LLM.

**Request:**
```bash
curl -X GET "http://localhost:8000/admin/llm/status" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Respuesta:**
```json
{
  "enabled": true,
  "provider": "openai",
  "model": "gpt-4.1-mini",
  "dry_run": false
}
```

## 4. Notas de Operación y Seguridad

- **Seguridad PII**: El sistema está diseñado para **no enviar** datos personales identificables (PII) al proveedor de LLM. Solo se envía el nombre del proveedor, el monto y el período de la factura.
- **Fallback**: Si `LLM_ENABLE` es `false`, falta la `OPENAI_API_KEY`, o la API de OpenAI falla, el sistema utilizará automáticamente un **mensaje de plantilla determinista**. Esto asegura que la funcionalidad de negociación nunca se interrumpa por completo.
- **Circuit Breaker**: (A implementar) En futuras versiones, un circuit breaker se abrirá tras fallos consecutivos, forzando el uso del fallback para proteger el sistema y evitar costes innecesarios.
- **Cache**: (A implementar) Las respuestas del LLM se cachearán para reducir la latencia y los costes en peticiones idénticas.
- **Dry Run**: Poner `LLM_DRY_RUN=true` es útil para testing, ya que evita llamadas reales a la API de OpenAI pero permite verificar el flujo de datos.
