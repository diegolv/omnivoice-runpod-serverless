import base64
import requests
import os
import time
import io
import wave
import re
import argparse

# 0. Leitor simples de .env (sem precisar do pip install python-dotenv)
if os.path.exists(".env"):
    with open(".env", "r") as f:
        for line in f:
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.strip().split("=", 1)
                os.environ[k.strip()] = v.strip().strip("\"'")

# 1. Autenticação e Configuração
RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY")
ENDPOINT_ID = os.getenv("RUNPOD_ENDPOINT_ID")

if not RUNPOD_API_KEY or not ENDPOINT_ID:
    print("❌ ERRO: Faltam as variáveis RUNPOD_API_KEY e RUNPOD_ENDPOINT_ID no arquivo .env!")
    exit(1)

URL = f"https://api.runpod.ai/v2/{ENDPOINT_ID}/runsync"

# 2. Argumentos de linha de comando
parser = argparse.ArgumentParser(description="Geração de clonagem de voz via OmniVoice Serverless")
parser.add_argument("--text", "-t", required=True, help="Arquivo .txt contendo o texto a ser falado")
parser.add_argument("--audio", "-a", required=True, help="Arquivo de áudio de referência (.mp3 ou .wav)")
parser.add_argument("--speed", "-s", type=float, default=1.0, help="Velocidade da fala (Padrão: 1.0)")
parser.add_argument("--steps", type=int, default=40, help="Passos de qualidade da IA (Padrão: 40)")
parser.add_argument("--guidance", type=float, default=2.5, help="Força de orientação de tom (Padrão: 2.5)")
args = parser.parse_args()

# Lê o texto
if not os.path.exists(args.text):
    print(f"❌ ERRO: Arquivo de texto '{args.text}' não encontrado!")
    exit(1)

with open(args.text, "r", encoding="utf-8") as text_file:
    TEXTO_COMPLETO = text_file.read().strip()

if not os.path.exists(args.audio):
    print(f"❌ ERRO: Arquivo de áudio '{args.audio}' não encontrado!")
    exit(1)

# 3. Função para fatiar textos longos
def split_text(text, max_length=600):
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current_chunk = ""
    for s in sentences:
        if len(current_chunk) + len(s) > max_length:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = s
        else:
            current_chunk += (" " if current_chunk else "") + s
    if current_chunk:
        chunks.append(current_chunk.strip())
    return [c for c in chunks if c.strip()]

chunks = split_text(TEXTO_COMPLETO)
print(f"Texto fatiado em {len(chunks)} parte(s).")

print("Formatando áudio de referência...")
with open(args.audio, "rb") as audio_file:
    audio_base64 = base64.b64encode(audio_file.read()).decode("utf-8")

headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "authorization": f"Bearer {RUNPOD_API_KEY}",
}

audio_fragments_bytes = []

# 4. Processar cada fatia
for idx, chunk in enumerate(chunks):
    print(f"\n--- Processando parte {idx+1}/{len(chunks)} ---")
    payload = {
        "input": {
            "text": chunk,
            "language": "pt",
            "reference_audio": audio_base64,
            "speed": args.speed,
            "num_step": args.steps,
            "guidance_scale": args.guidance
        }
    }
    
    print("Enviando requisição...")
    response = requests.post(URL, json=payload, headers=headers)
    
    if response.status_code != 200:
        print(f"Erro HTTP {response.status_code} na parte {idx+1}: {response.text}")
        continue
        
    response_data = response.json()
    job_id = response_data.get("id")
    status = response_data.get("status")
    
    # Polling
    while status in ["IN_QUEUE", "IN_PROGRESS"]:
        time.sleep(5)
        status_url = f"https://api.runpod.ai/v2/{ENDPOINT_ID}/status/{job_id}"
        status_response = requests.get(status_url, headers=headers)
        
        if status_response.status_code == 200:
            response_data = status_response.json()
            status = response_data.get("status")
            print(f"Status -> {status}")
        else:
            print(f"Erro ao checar status: {status_response.status_code}")
            break
            
    if status == "COMPLETED":
        output_data = response_data.get("output", {})
        audio_output_base64 = output_data.get("audio")
        
        if audio_output_base64:
            fragment_bytes = base64.b64decode(audio_output_base64)
            audio_fragments_bytes.append(fragment_bytes)
            print("✔️ Parte concluída e áudio armazenado.")
        else:
            print("❌ Erro: Resposta concluída, mas áudio vazio.")
    elif status == "FAILED":
        print(f"❌ Erro da IA na parte {idx+1}: {response_data}")

# 5. Juntar todos os áudios gerados
if audio_fragments_bytes:
    print("\n[+] Unindo todos os recortes de áudio...")
    nome_arquivo_final = "resultado_voz_clonada.wav"
    
    try:
        with wave.open(io.BytesIO(audio_fragments_bytes[0]), 'rb') as w_in_primeiro:
            params = w_in_primeiro.getparams()
            
        with wave.open(nome_arquivo_final, 'wb') as w_out:
            w_out.setparams(params)
            for fragmento in audio_fragments_bytes:
                with wave.open(io.BytesIO(fragmento), 'rb') as w_in:
                    w_out.writeframes(w_in.readframes(w_in.getnframes()))
                    
        print(f"🎉 SUCESSO! Áudio completo salvo como '{nome_arquivo_final}'!")
    except Exception as e:
        print("Erro ao unir arquivos WAV:", e)
else:
    print("\nNenhum áudio gerado com sucesso. Verifique sua chave da API, o log ou os créditos.")
