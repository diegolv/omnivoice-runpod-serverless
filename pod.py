import base64
import requests
import os
import time
import io
import wave
import re

# 1. Configurações de Autenticação do RunPod
RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY", "COLOQUE_SUA_API_KEY_AQUI")
ENDPOINT_ID = "sknkfkwaozfsgu"  # O ID gerado após criar o endpoint

URL = f"https://api.runpod.ai/v2/{ENDPOINT_ID}/runsync"

# 2. Configurações do seu Áudio de Referência (Os 10 segundos perfeitos)
AUDIO_INPUT_PATH = "sua_voz_10s.mp3"  # Pode ser .wav ou .mp3

# Lê o texto a ser falado do arquivo input.txt
with open("input.txt", "r", encoding="utf-8") as text_file:
    TEXTO_COMPLETO = text_file.read().strip()

# 3. Função para fatiar textos longos (Evita payload > 10MB no RunPod)
def split_text(text, max_length=600):
    # Divide por pontuação (pontos, exclamações, interrogações) para não cortar palavras
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

print(f"Texto fatiado inteligentemente em {len(chunks)} parte(s).")
print("Formatando áudio de referência...")
with open(AUDIO_INPUT_PATH, "rb") as audio_file:
    audio_base64 = base64.b64encode(audio_file.read()).decode("utf-8")

headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "authorization": f"Bearer {RUNPOD_API_KEY}",
}

audio_fragments_bytes = []

# 4. Processar cada fatia do texto no RunPod
for idx, chunk in enumerate(chunks):
    print(f"\n--- Processando parte {idx+1}/{len(chunks)} ---")
    payload = {
        "input": {
            "text": chunk,
            "language": "pt",
            "reference_audio": audio_base64,
            "speed": 1.0,               # Controle de velocidade (1.0 = normal, 1.2 = mais rápido)
            "num_step": 40,             # Qualidade de geração (padrão 32, 40+ tira ruidos, demora mais)
            "guidance_scale": 2.5       # Força a IA a seguir estritamente o seu tom de voz (padrão 2.0)
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
    
    # Polling da requisição assíncrona
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
            # Baixa e guarda na memória
            fragment_bytes = base64.b64decode(audio_output_base64)
            audio_fragments_bytes.append(fragment_bytes)
            print("✔️ Parte concluída e áudio armazenado.")
        else:
            print("❌ Erro: Resposta concluída, mas áudio vazio.")
    elif status == "FAILED":
        print(f"❌ Erro da IA na parte {idx+1}: {response_data}")

# 5. Juntar todos os áudios gerados perfeitamente em um único .wav
if audio_fragments_bytes:
    print("\n[+] Unindo todos os recortes de áudio (costura perfeita)...")
    nome_arquivo_final = "resultado_voz_clonada.wav"
    
    try:
        # Puxa os parâmetros (frequência, canais) do primeiro áudio
        with wave.open(io.BytesIO(audio_fragments_bytes[0]), 'rb') as w_in_primeiro:
            params = w_in_primeiro.getparams()
            
        with wave.open(nome_arquivo_final, 'wb') as w_out:
            w_out.setparams(params)
            # Acopla cada áudio na sequência
            for fragmento in audio_fragments_bytes:
                with wave.open(io.BytesIO(fragmento), 'rb') as w_in:
                    w_out.writeframes(w_in.readframes(w_in.getnframes()))
                    
        print(f"🎉 SUCESSO ABSOLUTO! Áudio completo de {len(chunks)} partes foi salvo como '{nome_arquivo_final}'!")
    except Exception as e:
        print("Erro ao unir arquivos WAV:", e)
else:
    print("\nNenhum áudio foi gerado com sucesso. Tente verificar o Endpoint ou a API Key.")
