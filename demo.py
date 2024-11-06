import asyncio
from fastapi import FastAPI, Request, File, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi_socketio import SocketManager
from fastapi.responses import HTMLResponse, JSONResponse
import json
import os
import random
import requests
import time

from openpibo.device import Device
from openpibo.motion import Motion
from openpibo.audio import Audio
from openpibo.speech import Speech
from threading import Timer
import rssdata

audio = Audio()
motion = Motion()
device = Device()
speech = Speech()

VOLUME = 100
TOPIC = '문헌정보실 테마도서'

app = FastAPI()
sio = SocketManager(app=app, cors_allowed_origins=[], mount_location="/ws/socket.io", socketio_path="")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

os.makedirs('mp3', exist_ok=True)
db = None

@app.get('/', response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Client connection events
@app.sio.on('connect')
async def connect(sid, environ):
    print(f"Client connected: {sid}")
    await sio.emit('date', {'date': db['date']})
    await sio.emit('volume', {'volume': VOLUME})

@app.sio.on('disconnect')
async def disconnect(sid):
    print(f"Client disconnected: {sid}")
    
@app.sio.on('update')
async def handle_update(sid):
    global db
    db = rssdata.update(TOPIC)
    await sio.emit('date', {'date': db['date']})
    return

@app.sio.on('change_volume')
async def change_volume(sid, data):
    global VOLUME
    VOLUME = data.get('volume', VOLUME)
    await sio.emit('volume', {'volume': VOLUME})
  
# STT function
def stt(filename="stream.wav", timeout=5, verbose=True):
    if verbose:
        os.system(f'arecord -D dmic_sv -c2 -r 16000 -f S32_LE -d {timeout} -t wav -q -vv -V stereo stream.raw; sox stream.raw -c 1 -b 16 {filename}; rm stream.raw')
    else:
        os.system(f'arecord -D dmic_sv -c2 -r 16000 -f S32_LE -d {timeout} -t wav -q stream.raw; sox stream.raw -q -c 1 -b 16 {filename}; rm stream.raw')

    response = requests.post('https://s-vapi.circul.us/stt/stt', files={'uploadFile':open(filename, 'rb')})
    if response.status_code != 200:
        raise Exception(f'response error: {response}')

    if response.json()['result'] == False:
        raise Exception(f'result error: {response.json()}')
    return response.json()['data']
   
async def talk(string, filepath, actions, key='msg1'):
    #print("[TTS]:", string)
    await sio.emit(key, {'text': string})
    await asyncio.sleep(0.1)
    if filepath == 'mp3/voice.mp3':
        speech.tts(string=string, filename=filepath, voice='gtts', lang='ko')
        await asyncio.sleep(0.1)
    
    device.eye_on(random.randint(100,255),random.randint(100,255),random.randint(100,255))
    if actions != None:
        motion_timer = Timer(0, motion.set_motion, args=(random.choice(actions),))
        motion_timer.start()
    audio.play(filepath, VOLUME, background=False)
    device.eye_off()
    await asyncio.sleep(0.5)
   
# Listen function using asyncio to prevent blocking
async def listen():
    device.eye_on(0, 255, 255)
    loop = asyncio.get_event_loop()
    ans = await loop.run_in_executor(None, stt, 'record.wav', 5, False)
    device.eye_off()
    return ans

# Touch sensor monitoring task
async def touch_sensor_monitor():
    state = False
    motion.set_motion('stop')
    
    while True:
        device.eye_on(50, 255, 50)

        if device.get_touch() == 'touch' and state == False:
            await talk('안녕, 나는 추천 도서 로봇 수정이야', 'mp3/hello.mp3', ['greeting'])
            motion.set_motion('stop')
            await asyncio.sleep(1)
            state = True

        if state == True:
            await talk('테마 별 도서를 소개해줄 수 있어', 'mp3/introduce_theme.mp3', None)
            for idx, item in enumerate(db['data']):
                await talk(f"{idx + 1}. {item['title']}", f'mp3/voice.mp3', ["speak_r1", "speak_l1"], 'msg2')

            motion.set_motion('stop')
            await talk('어떤 테마 번호의 도서 추천을 원해?', 'mp3/select_theme.mp3', None)

            ans = await listen()
            #print("[STT]:", ans)
            ans_text = ans.get('text', '') if isinstance(ans, dict) else ans
            await sio.emit('msg1', {'text': ans_text})
            n = 0
            for idx in range(len(db['data'])):
            	if str(idx+1) in ans_text:
                    n = idx+1
                    break

            if n > len(db['data']) or n < 1:
                await talk('잘못 선택했어, 다시 선택해줘', 'mp3/error.mp3', None)
                state = True
                continue

            # Send selected theme's book information
            selected_theme = db['data'][n - 1]
            await talk(f"{n}. {selected_theme['title']}", f'mp3/voice.mp3', None, 'msg2')
            await talk(f"책을 소개해줄게", 'mp3/introduce_book.mp3', None,)
            for i, item in enumerate(selected_theme['summary']):
                await talk(f"{i+1} 번째 도서, {item['data']}", f'mp3/voice.mp3', ["speak_r1", "speak_l1"], 'msg2')
                if i == 4:
                  break

            motion.set_motion('stop')
            await talk('더 추천을 원하면, "수정이" 없으면, "안녕" 이라고 해줘', 'mp3/select.mp3', None)
            
            ans = await listen()
            #print("[STT]:", ans)
            ans_text = ans.get('text', '') if isinstance(ans, dict) else ans
            await sio.emit('msg1', {'text': ans_text})

            if '수정' in ans_text:
                state = True
            elif '안녕' in ans_text:
                await talk('안녕, 좋은 하루 보내', 'mp3/bye.mp3', None)
                motion.set_motion('hand3', 2)
                state = False
            else:
                await talk('잘못 선택했어, 다시 선택해줘', 'mp3/error.mp3', None)
                state = False
            motion.set_motion('stop')            

        await asyncio.sleep(0.5)

        
# Start touch sensor monitoring on server startup
@app.on_event('startup')
async def startup_event():
    global db
    print('startup')
    db = rssdata.update(TOPIC)
    asyncio.create_task(touch_sensor_monitor())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run('demo:app', host='0.0.0.0', port=10001, access_log=False)
