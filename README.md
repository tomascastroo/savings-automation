# Savings Automation (SaaS de negociación de facturas con success-fee)

## Requisitos
- Docker y docker-compose
- (Opcional) Tesseract y Poppler si corrés fuera de Docker

## Variables de Entorno
Este proyecto usa un archivo `.env` para la configuración. Copia el `.env.example` a `.env` y ajústalo según sea necesario.
```bash
cp .env.example .env
```

## Levantar el stack
Asegúrate de tener Docker con Compose V2 (comando `docker compose`) instalado.
```bash
# Levanta todos los servicios en segundo plano
docker compose up --build -d
```
Una vez levantado, la API estará disponible en `http://localhost:8000`.

## Migraciones de Base de Datos
Este proyecto usa Alembic para gestionar las migraciones de la base de datos.

### Aplicar migraciones
Para llevar la base de datos a la última versión, ejecuta:
```bash
docker compose exec api alembic upgrade head
```

### Crear una nueva migración
Cuando hagas cambios en los modelos de `app/models/*.py`, crea una nueva migración:
```bash
docker compose exec api alembic revision --autogenerate -m "Un mensaje descriptivo del cambio"
```

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
- CRUD para Providers y Services
- Integración real Stripe/MercadoPago
- Bot WhatsApp (WABA)
- Jobs reales con RQ/Celery
