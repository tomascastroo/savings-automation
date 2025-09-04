# Savings Automation (SaaS de negociación de facturas con success-fee)

## Requisitos
- Docker y docker-compose
- (Opcional) Tesseract y Poppler si corrés fuera de Docker

## Variables de entorno (docker-compose ya define valores por defecto)
- `DATABASE_URL=postgresql+asyncpg://savings:savings@db:5432/savings`
- `REDIS_URL=redis://redis:6379/0`
- `JWT_SECRET=dev-secret-change-me`
- `ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173`
- `PAYMENT_GATEWAY=stripe|mp`
- `OPENAI_API_KEY` (opcional, si no está se mockea la respuesta)
- `STORAGE_DIR=/data`

## Levantar el stack
```bash
docker-compose up --build
```

Eso levanta:
- API FastAPI en `http://localhost:8000`
- Postgres en `localhost:5433`
- Redis en `localhost:6379`

## Endpoints básicos (curl)
### Signup
```bash
curl -sX POST http://localhost:8000/auth/signup -H "Content-Type: application/json"   -d '{"email":"test@example.com","password":"SuperSecret123"}'
```

### Login
```bash
TOKEN=$(curl -sX POST http://localhost:8000/auth/login -H "Content-Type: application/json"   -d '{"email":"test@example.com","password":"SuperSecret123"}' | jq -r .access_token)
echo $TOKEN
```

### Setup de pago (pre-autorización simulada)
```bash
curl -sX POST http://localhost:8000/auth/payments/setup -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json"   -d '{"provider":"stripe","pm_token":"pm_fake_123"}'
```

### Subir factura (PDF/JPG) y crear Bill
```bash
curl -s -F "file=@./tu_factura.pdf" "http://localhost:8000/bills?service_id=1" -H "Authorization: Bearer $TOKEN"
```

> **Nota**: Deberás crear primero un `Service` en la base (por ahora manualmente) asociado al `user_id` y `provider_id`.

### Negociar
```bash
curl -sX POST "http://localhost:8000/services/1/negotiate" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json"   -d '{"target_pct":0.20}'
```

### Confirmar negociación (genera Saving + Fee y cobra con idempotencia)
```bash
curl -sX POST "http://localhost:8000/negotiations/1/confirm" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json"   -d '{"new_amount":8000}'
```

### Dashboard
```bash
curl -s http://localhost:8000/dashboard/me -H "Authorization: Bearer $TOKEN"
```

## Notas de seguridad y calidad
- JWT HS256 con expiración configurable
- Rate limit 1 intento / 7 días por proveedor+cuenta+usuario
- Logging estructurado (JSON) con `structlog`
- Idempotencia de cobros usando Redis (`idem:fee:{id}`)
- OCR con Tesseract (PDFs soportados con `pdf2image`)

## Roadmap (TODO)
- Migraciones con Alembic
- CRUD para Providers y Services
- Integración real Stripe/MercadoPago
- Bot WhatsApp (WABA)
- Jobs reales con RQ/Celery
