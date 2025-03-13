from openpibo.motion import Motion
from openpibo.device import Device
from openpibo.speech import Speech
from openpibo.audio import Audio
import random, time

speech = Speech()
audio = Audio()
motion = Motion()
device = Device()

device.eye_off()
VOLUME = 100 # 음량
start = 0

MENT = '안녕하세요, 여기는 성남시, 수정 도서관 입니다.'
#speech.tts(string=MENT, filename='mp3/info.mp3', voice='gtts', lang='ko')

# 멘트 변경하실 때, 인터넷 연결 필요하고, 변경하셨으면 1회 speech.tts 앞에 # 을 제거하고 실행해주세요.
# 멘토 변경이 없으면 #speech.tts로 앞에 #을 두시면 그냥 mp3만 실행하게 되어 인터넷이 필요없습니다.

INTERVAL = 60 # 실행하는 주기 (초 단위) - 변경 필요하면 변경

while True:
  if time.time() - start > INTERVAL:
    start = time.time()
    device.eye_on(255,255,255)
    motion.set_motion(random.choice(['wave1','wave2','wave3','wave4','wave5','wave6']), 1)
    motion.set_motion('stop')
    audio.play('mp3/info.mp3', VOLUME, background=False)
    motion.set_motion('greeting', 2)
    motion.set_motion('stop')
    motion.set_motion('forward1')
    motion.set_motion('backward1')
    motion.set_motion('stop')    
    device.eye_off()
  time.sleep(1)
