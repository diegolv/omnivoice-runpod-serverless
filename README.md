# 🎙️ OmniVoice Serverless RunPod

![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)
![PyTorch](https://img.shields.io/badge/PyTorch-%23EE4C2C.svg?style=for-the-badge&logo=PyTorch&logoColor=white)
![RunPod](https://img.shields.io/badge/RunPod-Serverless-blueviolet?style=for-the-badge)

Uma API Serverless de alto desempenho para clonagem de voz e conversão de Texto em Fala (TTS) baseada no modelo state-of-the-art **OmniVoice** (`k2-fsa/OmniVoice`), otimizada para execução em GPUs através da infraestrutura Serverless do [RunPod](https://www.runpod.io/).

---

## ✨ Características

*   **⚡ Serverless / Cold Start Minimizado:** O modelo é inicializado globalmente no boot do container, evitando latência na inferência durante picos de requisição.
*   **🏎️ Otimizado para GPU:** Roda na última stack oficial da NVIDIA (CUDA 12.1) e faz inferência otimizada com PyTorch em FP16 (metade da precisão, dobrando a velocidade e economizando VRAM).
*   **🐋 Docker & CI/CD:** Contém *pipeline* automatizado do GitHub Actions. Faça um push e a imagem Docker já será reconstruída e enviada ao Docker Hub pronta para o RunPod.
*   **📡 Fácil Integração:** Comunicação inteiramente baseada em JSON e conversão nativa via codificação `Base64` do áudio, facilitando a vida do Frontend/Backend que consumir a API.

## 🚀 Como a API Funciona (Payloads)

A comunicação com o *worker* Serverless no RunPod ocorre enviando e recebendo arquivos de áudio codificados em Base64.

### Exemplo de Requisição (Entrada)

```json
{
  "input": {
    "text": "Olá, esta é uma demonstração de clonagem de voz utilizando inteligência artificial.",
    "language": "pt",
    "reference_audio": "UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA..." 
  }
}
```
*   `text`: O texto a ser falado pela IA.
*   `language`: O idioma desejado (padrão é `"pt"`).
*   `reference_audio`: A string de áudio em formato Base64 da voz base que você quer clonar.

### Exemplo de Resposta (Saída)

```json
{
  "audio": "UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA..."
}
```
O campo `audio` contém o resultado gerado (texto transformado em fala com a voz clonada) convertido num `.wav` e codificado em Base64.

## 🛠️ Build e Deploy (Pipeline Automatizado)

O projeto conta com uma [GitHub Action](.github/workflows/docker-build-push.yml) pré-configurada. 

1. Faça um Fork ou Clone deste repositório para o seu GitHub.
2. Adicione os **Secrets** do repositório no seu GitHub (`Settings > Secrets and variables > Actions`):
    *   `DOCKER_USERNAME`
    *   `DOCKER_PASSWORD`
3. Sempre que houver um `push` na branch `main`, a infraestrutura na nuvem se encarregará de fazer o Build e o Push da nova imagem ao Docker Hub, contornando a necessidade de espaço e processamento em sua máquina local.

## 💻 Testando Localmente

Caso queira testar a imagem do container na sua máquina local antes de mandar para nuvem (Necessário suporte a GPU e [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)):

```bash
# Faz o build da imagem
docker-compose build

# Roda o container
docker run --gpus all -p 8000:8000 sfdiego/omnivoice-runpod-serverless:latest
```

## 🏗️ Estrutura do Projeto

*   `app.py`: O "cérebro". Inicializa o OmniVoice, decodifica entradas, processa a clonagem e envia as respostas limpas.
*   `Dockerfile`: Configura o SO base (Ubuntu 22.04), instala FFmpeg, pacotes NVIDIA/CUDA e os requerimentos Python específicos.
*   `.github/workflows/`: Regras de automação CI/CD que criam a imagem remotamente.
