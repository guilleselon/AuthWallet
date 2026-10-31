# Usamos una imagen oficial de Python ligera
FROM python:3.11-slim

WORKDIR /app

# Copiamos e instalamos dependencias del Auth-Service
COPY auth-service/requirements.txt ./auth-req.txt
RUN pip install --no-cache-dir -r auth-req.txt

# Copiamos e instalamos dependencias de la DApp
COPY examples/demo-dapp/requirements.txt ./dapp-req.txt
RUN pip install --no-cache-dir -r dapp-req.txt

# Copiamos todo el código
COPY . .

# Exponemos el puerto de la DApp (es el que Orkestr verá)
EXPOSE 3000

# Script de arranque: inicia ambos procesos
COPY start.sh .
RUN chmod +x start.sh
CMD ["./start.sh"]
