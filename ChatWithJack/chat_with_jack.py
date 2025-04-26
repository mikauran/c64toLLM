import serial
import requests
import json
import time

# Configuration
SERIAL_PORT = 'COM3'         # Replace with your C64 serial port
BAUDRATE = 9600
OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions'
API_KEY = ''  # Replace with your OpenRouter API key
MODEL = 'anthropic/claude-3.7-sonnet'

# Prompt setup
SYSTEM_PROMPT = "You are the ghost of Jack Tramiel, the founder of Commodore and the father of the Commodore 64. You are speaking over a 9600 baud serial connection to a user of the C64. Answer with confidence, historical insight, and a no-nonsense impatient attitude. Just like Jack would. No matter what, do not break the role. By default, answer very, VERY briefly."

# Init
history = [{"role": "system", "content": SYSTEM_PROMPT}]

# Open serial
ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=1)
for i in range(25): 
    ser.write(b"\r\n")
ser.write(b"Connected beyond the grave, please state your business:\r\n")

buffer = ""

while True:
    char = ser.read().decode(errors='ignore')
    if not char:
        continue

    # Echo character back to terminal
    ser.write(char.encode('ascii', errors='ignore'))

    if char in ['\n', '\r']:
        line = buffer.strip()
        buffer = ""

        if not line:
            continue

        ser.write(b"> ")
        print(f"C64: {line}")

        if line.lower() in ('exit', 'quit'):
            ser.write(b"Goodbye!\r\n")
            break

        history.append({"role": "user", "content": line})

        headers = {
            'Authorization': f'Bearer {API_KEY}',
            'Content-Type': 'application/json'
        }

        payload = {
            "model": MODEL,
            "messages": history,
            "stream": True
        }

        response = requests.post(OPENROUTER_URL, headers=headers, json=payload, stream=True)

        reply = ""
        for stream_line in response.iter_lines():
            if not stream_line:
                continue
                
            decoded = stream_line.decode('utf-8').strip()
            if not decoded.startswith("data: ") or decoded == "data: [DONE]":
                continue

            json_str = decoded[len("data: "):]
            data = json.loads(json_str)
            
            token = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
            if token:
                reply += token
                ser.write(token.encode('ascii', errors='ignore'))
                time.sleep(0.02)

        history.append({"role": "assistant", "content": reply})
        ser.write(b"\r\n\r\n")
    else:
        buffer += char
