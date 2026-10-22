# 🎙️ Project AURA
**Automated Ultra-Responsive Assistant**

A 100% private, offline desktop voice assistant that runs entirely on a laptop. No cloud, no data leaves the machine.

## ✨ Current Features (Phase 1)
- 👂 **Speech-to-Text:** offline voice recognition using faster-whisper
- 🧠 **Local AI Brain:** Llama 3.2 (3B) running locally via Ollama, with conversation memory
- 🗣️ **Text-to-Speech:** natural offline voice using Piper TTS
- 🔁 **Voice Loop:** listen → think → speak, fully offline

## 🛠️ Tech Stack
| Module | Technology |
|---|---|
| Speech-to-Text | faster-whisper |
| Local LLM | Ollama + Llama 3.2 (3B) |
| Text-to-Speech | Piper TTS |
| Audio I/O | sounddevice, numpy |

## 🚀 Setup
1. Install **Python 3.11** and **[Ollama](https://ollama.com)**
2. Download the model:
```
   ollama pull llama3.2:3b
```
3. Create a virtual environment and install dependencies:
```
   py -3.11 -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
```
4. Download the Piper voice into a `voices/` folder:
   - [en_US-lessac-medium.onnx](https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx)
   - [en_US-lessac-medium.onnx.json](https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json)
5. Run:
```
   python aura_core.py
```

## 🗺️ Roadmap
- [x] **Phase 1:** Core engine (STT + LLM + TTS voice loop)
- [ ] **Phase 2:** App launcher, WhatsApp automation, live web search
- [ ] **Phase 3:** Floating PyQt6 UI + wake word ("Hey Jarvis")
- [ ] **Phase 4:** Optimization & latency tuning