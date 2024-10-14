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
VOLUME = 50
start = 0

while True:
  if time.time() - start > 60:
    start = time.time()
    device.eye_on(255,255,255)
    motion.set_motion(random.choice(['wave1','wave2','wave3','wave4','wave5','wave6']), 1)
    motion.set_motion('stop')
    #speech.tts(string='여기는 성남시, 수정 도서관 홍보 부스입니다.', filename='mp3/event.mp3', voice='gtts', lang='ko')
    audio.play('mp3/event.mp3', VOLUME, background=False)
    motion.set_motion('greeting', 2)
    motion.set_motion('stop')
    device.eye_off()
  time.sleep(1) 