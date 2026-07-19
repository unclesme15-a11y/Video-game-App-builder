# Nitro setup (GPU worker)

The Nitro is the muscle: local LLM inference and Unity builds. It's optional —
when it's off, LLM bulk work falls back to the cloud API and Unity jobs wait
in the queue.

Works fine on the Nitro's existing Windows install; no need to touch its OS.

## 1. Ollama (local models)

Install from https://ollama.com, then pull a small model that fits the
Nitro's VRAM (4–6GB → 7–8B quantized models):

```
ollama pull llama3.1:8b
```

By default Ollama only listens on localhost. To let the Acer reach it over
the LAN, set the environment variable `OLLAMA_HOST=0.0.0.0` and restart
Ollama. Then on the Acer, set `OLLAMA_URL=http://<nitro-ip>:11434` in `.env`.

## 2. Unity (for game builds)

Install Unity Hub + an editor version. Note the editor path, e.g.
`C:\Program Files\Unity\Hub\Editor\6000.0.x\Editor\Unity.exe`.

## 3. The worker

```powershell
pip install requests
$env:ACER_URL   = "http://<acer-ip>:8000"
$env:UNITY_PATH = "C:\Program Files\Unity\Hub\Editor\6000.0.x\Editor\Unity.exe"
python workers\gpu_worker.py
```

The worker polls the Acer every 10 seconds, runs whatever GPU jobs are
queued, and reports results back. Closing the laptop just pauses the flow —
nothing is lost.
