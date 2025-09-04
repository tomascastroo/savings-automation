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

## Flujo de Demo del MVP (End-to-End)

Esta guía muestra cómo simular el flujo completo del producto.

### 1. Preparación (Admin)
Primero, el administrador debe configurar un proveedor y un plan de ahorro. Usaremos el token del primer usuario (`id=1`) que, por defecto, es admin.

```bash
# Loguearse como admin (asumiendo que es el primer usuario registrado)
ADMIN_TOKEN=$(curl -sX POST http://localhost:8000/auth/login -H "Content-Type: application/json" -d '{"email":"admin@example.com","password":"secret123"}' | jq -r .access_token)

# Crear un proveedor (ej: Movistar)
PROVIDER_ID=$(curl -sX POST http://localhost:8000/admin/providers/ -H "Authorization: Bearer $ADMIN_TOKEN" -H "Content-Type: application/json" -d '{"name": "Movistar", "country": "AR"}' | jq -r .id)

# Crear un plan de ahorro para ese proveedor (más barato que la factura que subiremos)
curl -sX POST http://localhost:8000/admin/plans/ -H "Authorization: Bearer $ADMIN_TOKEN" -H "Content-Type: application/json" -d '{"provider_id": '$PROVIDER_ID', "name": "Plan Ahorro Fibra 300MB", "category": "internet", "price": 5000.0}'
```

### 2. Flujo de Usuario
Un usuario normal (que no es admin) se registra y utiliza el servicio.

```bash
# Registrar un nuevo usuario
curl -sX POST http://localhost:8000/auth/signup -H "Content-Type: application/json" -d '{"email":"test_user@example.com","password":"password123"}'

# Obtener su token
USER_TOKEN=$(curl -sX POST http://localhost:8000/auth/login -H "Content-Type: application/json" -d '{"email":"test_user@example.com","password":"password123"}' | jq -r .access_token)

# (Opcional) El usuario debe tener un "Service" con el proveedor. Por ahora, esto se crea manualmente o con un helper de test. Asumamos que el service_id=1 existe y pertenece al usuario.

# Subir una factura CARA (ej: una imagen cualquiera, el OCR está mockeado en tests pero la lógica de parsing funciona)
# El sistema la parseará y verá que el total ($10000) es mayor que el Plan de Ahorro ($5000)
curl -s -F "file=@./factura_cara.jpg" "http://localhost:8000/bills?service_id=1" -H "Authorization: Bearer $USER_TOKEN"
```

### 3. Negociación y Cobro
El sistema ahora tiene una oportunidad detectada.

```bash
# El usuario inicia la negociación para su servicio
NEG_ID=$(curl -sX POST "http://localhost:8000/services/1/negotiate" -H "Authorization: Bearer $USER_TOKEN" | jq -r .id)

# El usuario confirma la negociación exitosa (simulando que el bot tuvo éxito)
# El sistema calcula el ahorro ($10000 - $5000 = $5000) y la comisión (ej: 20% de $5000 = $1000)
curl -sX POST "http://localhost:8000/negotiations/$NEG_ID/confirm" -H "Authorization: Bearer $USER_TOKEN" -H "Content-Type: application/json"   -d '{"new_amount": 5000.0}'
```
El output del último comando mostrará que la comisión fue cobrada (`"payment_status": "paid"`).

### 4. Verificación (Admin)
El admin puede ver los resultados en el dashboard de KPIs.

```bash
curl -s http://localhost:8000/admin/kpis -H "Authorization: Bearer $ADMIN_TOKEN" | jq
```
El resultado mostrará `total_saving_achieved`, `total_fees_collected` y `successful_negotiations` actualizados.

## Roadmap (TODO)
- Integración real con gateways de pago (Stripe/MercadoPago)
- Integración real con LLMs para negociación
- Integración real con bots de mensajería (WhatsApp/Email)
- Jobs asíncronos robustos para OCR y negociación
- Interfaz de usuario (Frontend)
