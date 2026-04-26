# Bridge

Bridge is an accessibility prototype for deaf-blind learners. It converts classroom images and audio into short, essential explanations, then prepares that text for tactile playback on a motor-driven display.

## Inspiration

Many learning tools assume students can directly access visual or spoken information. We wanted to explore a different path: take classroom content, reduce it to the most important idea, and make it easier to present through a tactile interface.

## What it does

- Accepts image uploads or camera captures
- Accepts audio uploads or recordings
- Uses AI to reduce content to a short essential summary
- Splits the final text into 4-character chunks
- Sends those chunks to an ESP32 over serial for tactile display

## How it works

1. A user uploads an image or audio recording.
2. The backend generates a short essential summary.
3. The summary is normalized into simple text.
4. The text is split into 4-character chunks such as `a re`, `d ap`, `ple `.
5. The ESP32 firmware receives each chunk and moves 4 motors to the matching character positions.

## Repository structure

```text
frontend/
  index.html
  app.js
  style.css

backend/
  main.py
  audio.py
  vision.py
  summarizer.py
  serial_out.py
  braille.py
  requirements.txt

hardware/
  Braille_hardware.ino
```

## Tech stack

- Frontend: HTML, CSS, vanilla JavaScript
- Backend: Python, FastAPI, Uvicorn
- AI: Anthropic Claude
- Speech-to-text: faster-whisper
- Hardware communication: pyserial over USB serial
- Hardware: ESP32, 28BYJ-48 stepper motors, ULN2003 driver boards

## Features

- Image understanding for worksheets, slides, diagrams, and scenes
- Audio transcription and simplification
- Essential-summary output instead of long paragraphs
- Local serial transport for hardware testing
- Home page and demo UI for hackathon presentation

## Running locally

### 1. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

### 2. Start the backend

```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

### 3. Start the frontend

In a second terminal:

```bash
cd frontend
python3 -m http.server 4173 --bind 127.0.0.1
```

Then open:

- Frontend: [http://127.0.0.1:4173](http://127.0.0.1:4173)
- Backend health: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

## Environment variables

Create `backend/.env` with values like:

```env
ANTHROPIC_API_KEY=your_api_key_here
MOCK_CLAUDE=false
MOCK_TRANSCRIBE=false
ENABLE_DEVICE_IO=true
DEVICE_FORMAT=text4
SERIAL_PORT=your_serial_port_here
SERIAL_BAUD=115200
SERIAL_CHUNK_DELAY_MS=0
```

Notes:

- `SERIAL_CHUNK_DELAY_MS=0` means the ESP32 firmware controls the pause timing.
- The current firmware holds each 4-character chunk for 5 seconds before advancing.

## Hardware firmware

The current ESP32 firmware is:

- [hardware/Braille_hardware.ino](hardware/Braille_hardware.ino)

This firmware:

- listens on serial at `115200`
- receives 4-character chunks
- rotates 4 motors to calibrated character positions
- holds each chunk for a fixed delay
- advances to the next chunk

## API endpoints

- `POST /image`
- `POST /lecture`
- `GET /health`

## Challenges we ran into

- Balancing concise summaries with useful educational meaning
- Handling both image and audio flows in one interface
- Synchronizing backend chunking with physical motor movement
- Calibrating motor angles and pacing for readable tactile output

## Accomplishments

- Built a working full-stack demo
- Connected AI summarization to real serial hardware output
- Created a tactile 4-character prototype flow using an ESP32 and stepper motors
- Reduced image and audio input to essential text for accessible presentation

## What we learned

- Accessibility tooling needs strong UX, not just strong models
- Hardware timing and software timing need to be designed together
- Simplification is often more important than transcription alone

## Future work

- Move from 4-character output to a more braille-native tactile mechanism
- Add better homing/calibration for motor reliability
- Improve scene understanding and educational summarization quality
- Support more robust classroom workflows and real user testing


