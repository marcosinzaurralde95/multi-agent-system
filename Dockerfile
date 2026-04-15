# Usamos una versión ligera de Python
FROM python:3.11-slim

# Evitar que Python genere archivos .pyc y habilitar el buffer de logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instalar dependencias del sistema necesarias para Playwright y Dash
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    libgl1-mesa-glx \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Establecer directorio de trabajo
WORKDIR /app

# Copiar requirements primero para aprovechar el cache de Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instalar navegadores de Playwright
RUN playwright install chromium
RUN playwright install-deps chromium

# Copiar el resto del proyecto
COPY . .

# El puerto por defecto es 8050, pero el hosting lo puede cambiar
EXPOSE 8050

# Comando para iniciar la aplicación
CMD ["python", "start.py", "run", "--port", "8050"]
