#!/bin/bash
set -e

# Arranca el Auth-Service en el puerto 8080 (segundo plano)
echo "Starting Auth-Service..."
cd /app/services/auth-service
uvicorn src.auth_service.main:app --host 0.0.0.0 --port 8080 &
AUTH_PID=$!

# Arranca la DApp en el puerto 3000 (primer plano, para que Orkestr lo detecte)
echo "Starting Demo DApp..."
cd /app/examples/demo-dapp
# La DApp debe apuntar al auth-service en localhost:8080
export AUTH_URL="http://localhost:8080"
exec uvicorn src.demo_dapp.main:app --host 0.0.0.0 --port 3000
