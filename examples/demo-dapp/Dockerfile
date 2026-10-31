FROM python:3.12-slim

WORKDIR /app

# Copiamos desde la ruta exacta donde están los archivos de la dapp
COPY examples/demo-dapp/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el resto del código de la dapp
COPY examples/demo-dapp/src ./src

EXPOSE 8000
CMD ["uvicorn", "src.demo_dapp.main:app", "--host", "0.0.0.0", "--port", "8000"]
