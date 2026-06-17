import base64
import os
import uuid
import torch
import runpod
from omnivoice import OmniVoice
import soundfile as sf

# Inicializa o modelo globalmente no boot para economizar VRAM
print("Carregando o modelo OmniVoice na GPU...")
try:
    model = OmniVoice.from_pretrained(
        "k2-fsa/OmniVoice", 
        device_map="cuda:0", 
        dtype=torch.float16
    )
    print("Modelo carregado com sucesso!")
except Exception as e:
    print(f"Erro ao carregar o modelo: {e}")
    model = None

def handler(job):
    """Função que gerencia as requisições do RunPod Serverless"""
    job_input = job["input"]
    
    text = job_input.get("text")
    language = job_input.get("language", "pt")
    reference_audio_base64 = job_input.get("reference_audio")
    
    if not text or not reference_audio_base64:
        return {"error": "Dados incompletos. Informe o 'text' e o 'reference_audio' em base64."}
        
    if model is None:
        return {"error": "O modelo OmniVoice não foi carregado corretamente na inicialização."}

    # 1. Decodificar o áudio de referência recebido do script local
    job_id = job.get("id", str(uuid.uuid4()))
    temp_ref_path = f"/tmp/ref_input_{job_id}.mp3" # Salvando como MP3 para evitar confusão de formato
    try:
        with open(temp_ref_path, "wb") as f:
            f.write(base64.b64decode(reference_audio_base64))
    except Exception as e:
        return {"error": f"Falha ao decodificar áudio Base64: {str(e)}"}

    # 2. Executar a inferência de clonagem com o OmniVoice
    temp_out_path = f"/tmp/output_voice_{job_id}.wav"
    try:
        # Gera o áudio usando o nome correto de parâmetro 'ref_audio'
        audio_data = model.generate(
            text=text,
            language=language,
            ref_audio=temp_ref_path
        )
        
        # Tratamento robusto do formato de retorno do modelo
        if isinstance(audio_data, list):
            audio_array = audio_data[0]
            sr = 24000
        elif isinstance(audio_data, tuple):
            audio_array = audio_data[0]
            sr = audio_data[1] if len(audio_data) > 1 else 24000
        elif isinstance(audio_data, dict):
            audio_array = audio_data.get("audio", audio_data.get("wav"))
            sr = audio_data.get("sample_rate", audio_data.get("sr", 24000))
        else:
            audio_array = audio_data
            sr = 24000
            
        if hasattr(audio_array, 'cpu'):
            audio_array = audio_array.cpu().numpy()
            
        # Removemos dimensões extras (ex: de [1, N] para [N]) para o soundfile não reclamar
        import numpy as np
        if isinstance(audio_array, np.ndarray):
            audio_array = audio_array.squeeze()
            
        # Salva os dados gerados no arquivo temporário de saída
        sf.write(temp_out_path, audio_array, sr)
        
    except Exception as e:
        return {"error": f"Erro durante a geração do áudio pela IA: {str(e)}"}

    # 3. Converter o resultado (.wav final) para Base64 para enviar via API
    try:
        with open(temp_out_path, "rb") as f:
            output_base64 = base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        return {"error": f"Erro ao empacotar o áudio final: {str(e)}"}

    # Limpeza de arquivos temporários para não estourar o disco do container
    if os.path.exists(temp_ref_path): os.remove(temp_ref_path)
    if os.path.exists(temp_out_path): os.remove(temp_out_path)

    return {"audio": output_base64}

# Inicia o RunPod Worker
runpod.serverless.start({"handler": handler})
