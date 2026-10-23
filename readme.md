# 🎙️ Project AURA
**Automated Ultra-Responsive Assistant**

A private desktop voice assistant that runs locally on a laptop. Speech recognition, the AI brain, and the voice all run offline. The internet is used only for live web search and weather.

## ✨ Features
- 👂 **Speech-to-Text:** offline voice recognition using faster-whisper
- 🧠 **Local AI Brain:** Llama 3.2 (3B) via Ollama, with conversation memory and date awareness
- 🗣️ **Text-to-Speech:** natural offline voice using Piper TTS
- 🚦 **Intent Router:** instantly handles commands without waiting for the LLM
- 🖥️ **App & Website Launcher:** "Open Chrome", "Open LMS", "Open YouTube"
- 🌐 **Live Web Search:** fresh answers for news and current events using Tavily
- ☀️ **Live Weather:** real-time weather from Open-Meteo, with automatic fallback to web search
- 💬 **WhatsApp Messaging:** "Send a WhatsApp message to Ali saying I'm on my way"

## 🛠️ Tech Stack
| Module | Technology |
|---|---|
| Speech-to-Text | faster-whisper |
| Local LLM | Ollama + Llama 3.2 (3B) |
| Text-to-Speech | Piper TTS |
| Web Search | Tavily API |
| Weather | Open-Meteo API |
| Automation | subprocess, webbrowser, PyAutoGUI, WhatsApp URI |
| Audio I/O | sounddevice, numpy |

## 🚀 Setup
1. Install **Python 3.11**, **[Ollama](https://ollama.com)** and **WhatsApp Desktop**
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
5. Create a `.env` file with your [Tavily](https://tavily.com) key:
   ```
   TAVILY_API_KEY=your-key-here
   ```
6. Create a `contacts.json` file (numbers in international format, without +):
   ```json
   { "ali": "923001234567" }
   ```
7. Run:
   ```
   python aura_core.py
   ```

## 🗺️ Roadmap
- [x] **Phase 1:** Core engine (STT + LLM + TTS voice loop)
- [x] **Phase 2:** App launcher, live web search, live weather, WhatsApp automation
- [ ] **Phase 3:** Wake word ("Hey Jarvis") + floating PyQt6 UI
- [ ] **Phase 4:** Optimization & latency tuning