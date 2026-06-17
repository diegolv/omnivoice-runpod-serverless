import base64
import os
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
    temp_ref_path = "/tmp/ref_input.wav"
    try:
        with open(temp_ref_path, "wb") as f:
            f.write(base64.b64decode(reference_audio_base64))
    except Exception as e:
        return {"error": f"Falha ao decodificar áudio Base64: {str(e)}"}

    # 2. Executar a inferência de clonagem com o OmniVoice
    temp_out_path = "/tmp/output_voice.wav"
    try:
        # Gera o áudio (retorna os dados puros)
        audio_data = model.generate(
            text=text,
            language=language,
            reference_audio=temp_ref_path
        )
        
        # Salva os dados gerados no arquivo temporário de saída
        # O modelo costuma retornar um tensor ou array numpy. Ajustamos para salvar.
        sf.write(temp_out_path, audio_data.cpu().numpy() if hasattr(audio_data, 'cpu') else audio_data, 16000)
        
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
