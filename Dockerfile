# 1. Usa uma imagem oficial da NVIDIA com suporte a GPU (CUDA 12.1) e Ubuntu 22.04
FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04

# 2. Define variáveis de ambiente para evitar travamentos em prompts interativos durante a instalação
ENV DEBIAN_FRONTEND=noninteractive

# 3. Instala as dependências essenciais do sistema operacional (FFmpeg para áudio e Git para pacotes)
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-dev \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# 4. Atualiza o gerenciador de pacotes do Python (pip)
RUN pip3 install --no-cache-dir --upgrade pip

# 5. Instala o PyTorch e pacotes de áudio PRIMEIRO com suporte a GPU (CUDA 12.1)
RUN pip3 install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# 6. DEPOIS instala os pacotes normais (assim o omnivoice aproveita o torch correto)
RUN pip3 install --no-cache-dir runpod soundfile omnivoice

# 7. Configura o diretório de trabalho dentro do container
WORKDIR /app

# 8. Copia o script do nosso "garçom" (cérebro da API) para dentro do container
COPY app.py /app/app.py

# 9. Comando que o RunPod Serverless vai disparar automaticamente ao iniciar a máquina
CMD [ "python3", "-u", "app.py" ]
