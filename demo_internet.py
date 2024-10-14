import json
import os
import time
import requests
import random

from openpibo.device import Device
from openpibo.motion import Motion
from openpibo.audio import Audio
from openpibo.speech import Speech

audio = Audio()
motion = Motion()
device = Device()
speech = Speech()
VOLUME = 100

try:
  with open('record.json', 'r', encoding='utf-8') as f:
    res = json.load(f)
except Exception as ex:
  res = None
  print(str(ex))
  
os.system('mkdir -p mp3')

def stt(self, filename="stream.wav", timeout=5, verbose=True):
  if verbose == True:
    os.system(f'arecord -D dmic_sv -c2 -r 16000 -f S32_LE -d {timeout} -t wav -q -vv -V streo stream.raw;sox stream.raw -c 1 -b 16 {filename};rm stream.raw')
  else:
    os.system(f'arecord -D dmic_sv -c2 -r 16000 -f S32_LE -d {timeout} -t wav -q stream.raw;sox stream.raw -q -c 1 -b 16 {filename};rm stream.raw')

  response = requests.post('https://s-vapi.circul.us/stt/stt', files={'uploadFile':open(filename, 'rb')})
  if response.status_code != 200:
    raise Exception(f'response error: {response}')

  if response.json()['result'] == False:
    raise Exception(f'result error: {response.json()}')
  return response.json()['data']  
  
def talk(string, filepath, actions, delay=1):
  print("[TTS]:", string)  
  device.eye_on(255,255,0)
  #speech.tts(string=string, filename=filepath, voice='gtts', lang='ko')
  audio.play(filepath, VOLUME)
  if actions != None:
    motion.set_motion(random.choice(actions))
  time.sleep(delay)
  device.eye_off()
  
def listen():
  print("[STT]-Start")
  device.eye_on(0,255,255)
  ans = stt('record.wav', verbose=False)
  device.eye_off()
  print("[STT]-End")
  return ans

state = False
motion.set_motion('stop')
while True:
  device.eye_on(50,255,50)

  if device.get_touch() == 'touch' and state == False:
    talk('안녕, 나는 추천 도서 로봇 수정이야', 'mp3/hello.mp3', ['greeting'])
    motion.set_motion('stop')
    time.sleep(1)
    state = True
    
    # '무슨 테마가 있어' 음성인식/입력 이후 동작이 없어서 의미 없음
    
  if state == True:
    themes = ''
    talk('테마 별 도서를 소개해줄 수 있어', 'mp3/introduce_theme.mp3', None, 3)
    for idx, item in enumerate(res['data']):
      talk(f"{idx + 1}. {item['title']}", f'mp3/theme{idx + 1}.mp3', ["speak_r1","speak_l1"], 2)
 
    motion.set_motion('stop')
    talk('어떤 테마 번호의 도서 추천을 원해?', 'mp3/select_theme.mp3', None, 6)

    # 00 테마 추천해줘. 테마 이름이 복잡하여, 비교 어려움 / 테마 번호로 대체함
    ans = listen()["text"]
    print("[STT]:", ans)
    
    if '1번' in ans or '1' in ans or '일번' in ans or 'Ilbrunn' in ans or '일본' in ans:
      n = 1
    elif '2번' in ans or '2' in ans or '이번' in ans:
      n = 2
    elif '3번' in ans or '3' in ans or '삼번' in ans:
      n = 3
    else:
      n = 0

    if n > len(res['data']) or n < 1:
      talk('잘못 선택했어, 다시 선택해줘', 'mp3/error.mp3', None, 4)
      state = True
      continue

    # 선택한 테마의 도서 정보 전송
    selected_theme = res['data'][n - 1]
    talk(f"{n}. {selected_theme['title']}", f'mp3/theme{n}.mp3', None, 5)
    talk(f"책을 소개해줄게", 'mp3/introduce_book.mp3', None, 3) 
    for i, item in enumerate(selected_theme['summary']):
      talk(f"{idx+1} 번째 도서, {item['data']}", f'mp3/book{n}_{i}.mp3', ["speak_r1","speak_l1"], 1)

    motion.set_motion('stop')
    talk('더 추천을 원하면, "수정도서관" 없으면, "안녕" 이라고 해줘', 'mp3/select.mp3', None, 6)
    ans = listen()["text"]
    print("[STT]:", ans)

    if '수정도서관' in ans or '수정 도서관' in ans:
      state = True
    elif '안녕' in ans :
      talk('안녕, 처음부터 다시 시작할게', 'mp3/bye.mp3', None, 1)
      motion.set_motion('hand3', 2)
      motion.set_motion('stop')
      state = False      
    else:
      talk('잘못 선택했어, 다시 선택해줘', 'mp3/error.mp3', None, 1)
      state = False

  time.sleep(0.5)
