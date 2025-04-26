import serial
import requests
import json
import time

# Load settings
def load_settings():
    with open('settings.json', 'r') as f:
        return json.load(f)

def log(message):
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")

# Initial load
config = load_settings()
SERIAL_PORT = config['serial_port']
BAUDRATE = config['baudrate']

# Open serial
ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=1)
log(f"Serial port {SERIAL_PORT} opened at {BAUDRATE} baud.")

for _ in range(25):
    ser.write(b"\r\n")
ser.write(b"C64 connected to ChatGPT. READY.\r\n")
log("Sent initial connection message to C64.")

buffer = ""

# Initialize history
SYSTEM_PROMPT = config['system_prompt']
history = [{"role": "system", "content": SYSTEM_PROMPT}]

def build_payload(history, config):
    payload = {
        "model": config.get('openai_model', 'gpt-3.5-turbo'),
        "messages": history,
        "temperature": config.get('temperature', 0.7)
    }
    log(f"Built payload: {json.dumps(payload)[:300]}...")
    return payload

while True:
    try:
        char = ser.read().decode(errors='ignore')
    except Exception as e:
        log(f"Error reading serial: {e}")
        continue

    if not char:
        continue

    ser.write(char.encode('ascii', errors='ignore'))

    if char in ['\n', '\r']:
        line = buffer.strip()
        buffer = ""

        if not line:
            continue

        ser.write(b"> ")
        log(f"Received from C64: '{line}'")

        if line.lower() in ('exit', 'quit'):
            ser.write(b"Goodbye!\r\n")
            log("Exit command received. Shutting down.")
            break

        try:
            config = load_settings()
            OPENAI_URL = config['openai_url']
            API_KEY = config['api_key']

            if 'system_prompt' in config and history and config['system_prompt'] != SYSTEM_PROMPT:
                SYSTEM_PROMPT = config['system_prompt']
                history = [{"role": "system", "content": SYSTEM_PROMPT}]
                log("System prompt reloaded from settings.")

        except Exception as e:
            log(f"Error reloading settings: {e}")
            continue

        history.append({"role": "user", "content": line})
        log("Appended user input to history.")

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {API_KEY}'
        }

        payload = build_payload(history, config)

        try:
            log(f"Sending POST request to OpenAI Chat API...")
            response = requests.post(
                OPENAI_URL,
                headers=headers,
                json=payload,
                timeout=30
            )
            log("Request sent, awaiting response...")
        except Exception as e:
            log(f"Request failed: {e}")
            ser.write(b"\r\n[Error contacting AI]\r\n")
            continue

        if response.status_code != 200:
            log(f"Error response from OpenAI: {response.text}")
            ser.write(b"\r\n[Error from AI]\r\n")
            continue

        try:
            data = response.json()
            reply = data['choices'][0]['message']['content']
            log(f"AI Reply: {reply[:100]}...")
        except Exception as e:
            log(f"Error parsing AI response: {e}")
            reply = "Error parsing AI response."

        if reply:
            history.append({"role": "assistant", "content": reply})
            ser.write(b"\r\n")  # <<< ADD newline here before printing reply
            for c in reply:
                ser.write(c.encode('ascii', errors='ignore'))
                time.sleep(0.02)

        ser.write(b"\r\n\r\n")
    else:
        buffer += char
