import asyncio
from fastapi import FastAPI, Request, File, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi_socketio import SocketManager
from fastapi.responses import HTMLResponse, JSONResponse
import json
import os
import random

# 기존 임포트 유지
from openpibo.device import Device
from openpibo.motion import Motion
from openpibo.audio import Audio
from openpibo.speech import Speech

audio = Audio()
motion = Motion()
device = Device()
speech = Speech()
VOLUME = 50

app = FastAPI()
sio = SocketManager(app=app, cors_allowed_origins=[], mount_location="/ws/socket.io", socketio_path="")

os.system('mkdir -p mp3')
# 정적 파일 경로 설정
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get('/', response_class=HTMLResponse)
async def f(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# out.json 파일 로드
try:
    with open('record.json', 'r', encoding='utf-8') as f:
        res = json.load(f)
except Exception as ex:
    res = None
    print(str(ex))

# 터치 센서 모니터링 함수
async def touch_sensor_monitor():
    motion.set_motion('stop')
    device.eye_on(50,255,50)
    while True:
        if device.get_touch() == 'touch':
            # 터치 이벤트 처리
            await handle_touch_event()
            # 중복 감지를 피하기 위해 잠시 대기
            await asyncio.sleep(0.5)
        else:
            await asyncio.sleep(0.1)

async def talk(string, filepath, actions, delay=1):
  device.eye_on(255,255,0)
  #speech.tts(string=string, filename=filepath, voice='gtts', lang='ko')
  print("[TTS]:", string)
  await sio.emit('message', {'text': string})
  await asyncio.sleep(0.1)
  audio.play(filepath, VOLUME)
  if actions != None:
    motion.set_motion(random.choice(actions))
  await asyncio.sleep(delay)
  device.eye_off()
    
# 터치 이벤트 처리 함수
async def handle_touch_event():
    # 모든 클라이언트에게 이벤트 전달
    await talk('안녕, 나는 추천 도서 로봇 수정이야', 'mp3/hello.mp3', ['greeting'])
    motion.set_motion('stop')
    await asyncio.sleep(1)
    
    await talk('테마 별 도서를 소개해줄 수 있어', 'mp3/introduce_theme.mp3', None, 3)
    if res == None:
        await sio.emit('message', {'text': '테마 데이터 없음'})
        return
    
    # 테마 목록 전송
    themes = ''     
    for idx, item in enumerate(res['data']):
        await talk(f"{idx + 1}. {item['title']}", f'mp3/theme{idx + 1}.mp3', ["speak_r1","speak_l1"], 2)
    
    motion.set_motion('stop')
    await sio.emit('prompt', {'text': f'1 에서 {len(res["data"])} 까지 테마 번호만 입력하세요.'})
    await talk('어떤 테마 번호의 도서 추천을 원해?', 'mp3/select_theme.mp3', None)

# 서버 시작 시 터치 센서 모니터링 작업 실행
@app.on_event('startup')
async def startup_event():
    print('startup')
    asyncio.create_task(touch_sensor_monitor())

# 클라이언트 연결 시 이벤트 처리
@app.sio.on('connect')
async def connect(sid, environ):
    print(f"Client connected: {sid}")

# 클라이언트 연결 해제 시 이벤트 처리
@app.sio.on('disconnect')
async def disconnect(sid):
    print(f"Client disconnected: {sid}")

# 클라이언트로부터의 입력 처리
@app.sio.on('input')
async def handle_input(sid, data):
    user_input = data.get('text', '').strip()

    if res == None:
        await sio.emit('message', {'text': '테마 데이터 없음'})
        return
    
    # 입력에 따라 처리
    try:
        n = int(user_input)
        if n > len(res['data']) or n < 1:
            await talk('잘못 선택했어, 다시 선택해줘', 'mp3/error.mp3', None)     
            return

        # 선택한 테마의 도서 정보 전송
        selected_theme = res['data'][n - 1]
        await talk(f"{n}. {selected_theme['title']}", f'mp3/theme{n}.mp3', None, 6)
        await talk(f"책을 소개해줄게", 'mp3/introduce_book.mp3', None, 3) 
        for idx, item in enumerate(selected_theme['summary']):
            await talk(item['data'], f'mp3/book{n}_{idx}.mp3', ["speak_r1","speak_l1"], 1)
        
        await sio.emit('prompt', {'text': '<<수정도서관>> 또는 <<안녕>> 을 입력하세요.'})
        await talk('더 추천을 원하면, "수정도서관" 없으면, "안녕" 이라고 해줘', 'mp3/select.mp3', None)        
    except ValueError:
        if user_input == '수정도서관':
            # 다시 테마 목록 전송
            themes = ''     
            for idx, item in enumerate(res['data']):
                await talk(f"{idx + 1}. {item['title']}\n", f'mp3/theme{idx + 1}.mp3', ["speak_r1","speak_l1"], 2)

            motion.set_motion('stop')
            await sio.emit('prompt', {'text': f'1 에서 {len(res["data"])} 까지 테마 번호만 입력하세요.'})
            await talk('어떤 테마 번호의 도서 추천을 원해?', 'mp3/select_theme.mp3', None)
        elif user_input == '안녕':
            await talk('안녕, 처음부터 다시 시작할게', 'mp3/bye.mp3', None)
            pass
        else:
            await talk('잘못 선택했어, 다시 선택해줘', 'mp3/error.mp3', None)     
            
# 파일 업로드 엔드포인트 추가
@app.post('/upload')
async def upload_file(file: UploadFile = File(...)):
    if file.content_type != 'application/json':
        return JSONResponse(status_code=400, content={'status': 'error', 'message': 'JSON 파일만 업로드할 수 있습니다.'})
    try:
        contents = await file.read()
        data = json.loads(contents)
        with open('record.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        # 업로드된 내용을 다시 로드하여 반영
        global res
        res = data
        return {'status': 'success', 'message': '파일이 성공적으로 업로드되었습니다.'}
    except json.JSONDecodeError:
        return JSONResponse(status_code=400, content={'status': 'error', 'message': '유효한 JSON 파일이 아닙니다.'})
    except Exception as e:
        return JSONResponse(status_code=500, content={'status': 'error', 'message': f'파일 업로드 중 오류가 발생했습니다: {e}'})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run('server:app', host='0.0.0.0', port=10001, access_log=False)
