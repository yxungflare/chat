import asyncio
import uuid
import mimetypes
import base64
import aiohttp
import pyaudio
import wave
import os

from IPython.display import display

from pywebio import start_server
from pywebio.input import *
from pywebio.output import *
from pywebio.session import defer_call, info as session_info, run_async, run_js

import os
from dotenv import load_dotenv

load_dotenv()

chat_msgs = []
online_users = set()

PASSWORD_INPUT = os.getenv("PASSWORD")

MAX_MESSAGES_COUNT = 3




CSS = '''
<style>
    *{
        
    }
  .webio-theme-default {
        
        opacity: 0.9;
        background-repeat: no-repeat;
        background-size: cover;
        background-position: center;
        }
    #input-container{
            z-index: 0;
            background: none;
            position: static;
            height: fit-content;
            box-shadow: none;
            margin-top: 0;
            margin-bottom: 40px;
    }
    .markdown-body{
        background-color: white;
        z-index: 100;
    }
</style>
'''

counter = 0

async def record_audio():
    global counter
    # audio
    chunk = 1024  # Запись кусками по 1024 сэмпла
    sample_format = pyaudio.paInt16  # 16 бит на выборку
    channels = 2
    rate = 44100  # Запись со скоростью 44100 выборок(samples) в секунду
    seconds = 3

    counter += 1

    filename = f"./static/audio_records/output_sound_{counter}.wav" # Создать файл 'output_sound + {nickname} + {counter}'.mp3
    p = pyaudio.PyAudio()  # Создать интерфейс для PortAudio
    print('Recording...')
    stream = p.open(format=sample_format,
                    channels=channels,
                    rate=rate,
                    frames_per_buffer=chunk,
                    input_device_index=1,  # индекс устройства с которого будет идти запись звука
                    input=True)
    
    frames = []  # Инициализировать массив для хранения кадров
    

    

    # Хранить данные в блоках в течение 3 секунд
    for i in range(0, int(rate / chunk * seconds)):
        data = stream.read(chunk)
        frames.append(data)
    
    # Остановить и закрыть поток
    stream.stop_stream()
    stream.close()
    # Завершить интерфейс PortAudio
    p.terminate()
    
    print('Finished recording!')

    # Сохранить записанные данные в виде файла WAV
    wf = wave.open(filename, 'wb')
    wf.setnchannels(channels)
    wf.setsampwidth(p.get_sample_size(sample_format))
    wf.setframerate(rate)
    wf.writeframes(b''.join(frames))
    wf.close()
    
    audio = put_html('''
        <audio src="{}" controls>
            Your browser does not support the audio element.
        </audio>
    '''.format(filename))
    
    return audio


async def main():
    global chat_msgs

    put_html(CSS)  # добавить CSS стиль

    put_markdown("## ⭐ Добро пожаловать в мессенджер Военной академии связи!")

    msg_box = output()
    put_scrollable(msg_box, height=300, keep_bottom=True)

    nickname = await input("Введите логин", required=True, placeholder="Ваш логин", validate=lambda n: "Такой логин уже используется!" if n in online_users or n == '📢' else None)
    online_users.add(nickname)
    password = await input("Введите пароль", required=True, placeholder="Введите пароль", type=PASSWORD)
    if password == PASSWORD_INPUT:
        chat_msgs.append(('✔️', 'message', f'`{nickname}` присоединился к чату!'))
        msg_box.append(put_markdown(f'✔️ `{nickname}` присоединился к чату'))

        refresh_task = run_async(refresh_msg(nickname, msg_box))

        while True:
            data = await input_group("💭 Новое сообщение", [
                input(placeholder="Текст сообщения ...", name="msg"),
                file_upload('Выберете изображение...',
                            accept="image/*", multiple=True, name='img'),
                actions(name="cmd", buttons=["Отправить", "Записать голосовое сообщение", {
                        'label': "Выйти из чата", 'type': 'cancel'}])
            ], validate=lambda m: ('msg', "Введите текст сообщения!") if m["cmd"] == "Отправить" and not m['msg'] and not m['img'] else None)

            if data is None:
                break

            if data['img']:
                up_img = data['img']
                for file in up_img:
                    if file['content']:
                        file_type = mimetypes.guess_type(file['filename'])[0]
                        img_content = base64.b64encode(
                            file['content']).decode('utf-8')
                        msg_box.append(put_markdown(f"`{nickname}`:"))
                        msg_box.append(
                            put_image(src='data:'+file_type+';base64,'+img_content, width='170px'))
                        chat_msgs.append(
                            (nickname, 'image', file['filename'], img_content, file_type))

            if data['msg']:
                msg_box.append(put_markdown(f"`{nickname}`: {data['msg']}"))
                chat_msgs.append((nickname, 'message', data['msg']))

            if data['cmd'] == 'Записать голосовое сообщение':
                audio_content = await record_audio()
                msg_box.append(put_markdown(f"`{nickname}`:"))
                msg_box.append(audio_content)
                chat_msgs.append((nickname, 'audio', audio_content))

        refresh_task.close()

        online_users.remove(nickname)
        toast("Вы вышли из чата!")
        msg_box.append(put_markdown(
            f'❗ Пользователь `{nickname}` покинул чат!'))
        chat_msgs.append(('❗', 'message', f'Пользователь `{nickname}` покинул чат!'))

        put_buttons(['Перезайти'], onclick=lambda btn: run_js(
            'window.location.reload()'))
    else:
        msg_box.append(put_markdown('❗ Пароль не верный!'))

        refresh_task = run_async(refresh_msg('Ooops!', msg_box))


async def refresh_msg(nickname, msg_box):
    global chat_msgs
    last_idx = len(chat_msgs)
    
    while True:
        await asyncio.sleep(1)
        print(len(chat_msgs[last_idx:]))
        for m in chat_msgs[last_idx:]:
            if m[0] != nickname:  # if not a message from current user
                if m[1] == 'image':
                    msg_box.append(put_markdown(f"`{m[0]}`:"))
                    msg_box.append(
                        put_image(src='data:'+m[2]+';base64,'+m[3], width='170px'))
                elif m[1] == 'audio':
                    msg_box.append(put_markdown(f"`{m[0]}`:"))
                    msg_box.append(m[2])
                
                elif m[1] == 'message':
                    msg_box.append(put_markdown(f"`{m[0]}`: {m[2]}"))

                # print(len(chat_msgs))
        
        # remove expired messages and files
        if len(chat_msgs) > MAX_MESSAGES_COUNT:
            half_len = len(chat_msgs)//2
            
            # remove files in ./static/audio_records folder
            folder = './static/audio_records'
            files = os.listdir(folder)    
            for file_name in files[:1]:
                file_path = os.path.join(folder, file_name)
                os.remove(file_path)
            
            # remove expired messages
            chat_msgs = chat_msgs[half_len:]
            last_idx = len(chat_msgs)
                

if __name__ == "__main__":
    start_server(main, debug=True, port=8080, cdn=True,
                 static_dir='./static', host="127.0.0.1")