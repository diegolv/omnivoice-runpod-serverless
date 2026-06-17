import base64
import requests
import os

# 1. Configurações de Autenticação do RunPod
RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY", "COLOQUE_SUA_API_KEY_AQUI")
ENDPOINT_ID = "mel78qy7cbsj9m"  # O ID gerado após criar o endpoint

URL = f"https://api.runpod.ai/v2/{ENDPOINT_ID}/runsync"

# 2. Configurações do seu Áudio de Referência (Os 10 segundos perfeitos)
AUDIO_INPUT_PATH = "sua_voz_10s.mp3"  # Pode ser .wav ou .mp3
TEXTO_PARA_FALAR = (
    "Olá! Esta é a minha própria voz sendo gerada localmente através "
    "do OmniVoice rodando no RunPod Serverless. O resultado ficou incrível!"
)

# 3. Converter o áudio de referência para string Base64
print("Formatando áudio de referência...")
with open(AUDIO_INPUT_PATH, "rb") as audio_file:
    audio_base64 = base64.b64encode(audio_file.read()).decode("utf-8")

# 4. Montar o payload (comando) no padrão esperado pelo container do OmniVoice
payload = {
    "input": {
        "text": TEXTO_PARA_FALAR,
        "language": "pt",  # Idioma português
        "reference_audio": audio_base64,
    }
}

headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "authorization": f"Bearer {RUNPOD_API_KEY}",
}

import time

# 5. Enviar a requisição para a GPU do RunPod
print("Enviando requisição para a GPU do RunPod... (Aguarde alguns segundos)")
response = requests.post(URL, json=payload, headers=headers)

if response.status_code == 200:
    response_data = response.json()
    job_id = response_data.get("id")
    status = response_data.get("status")
    
    print(f"Job criado! ID: {job_id} | Status Inicial: {status}")
    
    # Loop de Polling: Pergunta ao servidor o status a cada 3 segundos
    while status in ["IN_QUEUE", "IN_PROGRESS"]:
        print("Processando na GPU... Aguardando 5 segundos.")
        time.sleep(5)
        
        status_url = f"https://api.runpod.ai/v2/{ENDPOINT_ID}/status/{job_id}"
        status_response = requests.get(status_url, headers=headers)
        
        if status_response.status_code == 200:
            response_data = status_response.json()
            status = response_data.get("status")
            print(f"Status atualizado: {status}")
        else:
            print(f"Erro ao checar status: {status_response.status_code}")
            break

    # O RunPod Serverless retorna o status do job. Se der 'COMPLETED':
    if status == "COMPLETED":
        # Dependendo do container, o áudio pode vir como string base64 no JSON
        # ou como um link de download. Vamos assumir o padrão base64:
        audio_output_base64 = response_data["output"].get("audio")

        if audio_output_base64:
            # Salva o arquivo de áudio clonado final
            nome_arquivo_final = "resultado_voz_clonada.wav"
            with open(nome_arquivo_final, "wb") as f_output:
                f_output.write(base64.b64decode(audio_output_base64))
            print(f"🎉 Sucesso! Áudio gerado e salvo como '{nome_arquivo_final}'")
        else:
            print("Formato de resposta inesperado do container:", response_data)
    elif status == "FAILED":
        print(f"Erro no processamento do Job. Resposta completa: {response_data}")
else:
    print(f"Erro na requisição HTTP: {response.status_code}")
    print(response.text)
