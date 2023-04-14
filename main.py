import asyncio
import uuid
import mimetypes
import base64

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

MAX_MESSAGES_COUNT = 100


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

async def main():
    global chat_msgs

    put_html(CSS) # добавить CSS стиль
    
    put_markdown("## ⭐ Добро пожаловать в мессенджер Военной академии связи!")

    msg_box = output()
    put_scrollable(msg_box, height=300, keep_bottom=True)

    nickname = await input("Введите логин", required=True, placeholder="Ваш логин", validate=lambda n: "Такой логин уже используется!" if n in online_users or n == '📢' else None)
    online_users.add(nickname)
    password = await input("Введите пароль", required=True, placeholder="Введите пароль", type=PASSWORD)
    if password == PASSWORD_INPUT:
        chat_msgs.append(('✔️', f'`{nickname}` присоединился к чату!'))
        msg_box.append(put_markdown(f'✔️ `{nickname}` присоединился к чату'))

        refresh_task = run_async(refresh_msg(nickname, msg_box))

        while True:
            data = await input_group("💭 Новое сообщение", [
                input(placeholder="Текст сообщения ...", name="msg"),
                file_upload('Выберете изображение...', accept="image/*", multiple=True, name='img'),
                actions(name="cmd", buttons=["Отправить", {'label': "Выйти из чата", 'type': 'cancel'}])
            ], validate = lambda m: ('msg', "Введите текст сообщения!") if m["cmd"] == "Отправить" and not m['msg'] else None)
            
            if data is None:
                break

            if data['img']:
                up_img = data['img']
                for file in up_img:
                    if file['content']:
                        file_type = mimetypes.guess_type(file['filename'])[0]
                        img_content = base64.b64encode(file['content']).decode('utf-8')
                        msg_box.append(put_markdown(f"`{nickname}`: {put_image(src='data:'+file_type+';base64,'+img_content, width='170px')}"))
                        chat_msgs.append((nickname, file['filename'], img_content))

            if data['msg']:
                msg_box.append(put_markdown(f"`{nickname}`: {data['msg']}"))
                chat_msgs.append((nickname, data['msg']))

        refresh_task.close()

        online_users.remove(nickname)
        toast("Вы вышли из чата!")
        msg_box.append(put_markdown(f'❗ Пользователь `{nickname}` покинул чат!'))
        chat_msgs.append(('❗', f'Пользователь `{nickname}` покинул чат!'))

        put_buttons(['Перезайти'], onclick=lambda btn:run_js('window.location.reload()'))
    else:
        chat_msgs.append(('❗',  'Пароль не верный!'))
        msg_box.append(put_markdown('❗ Пароль не верный!'))

        refresh_task = run_async(refresh_msg('Ooops!', msg_box))

async def refresh_msg(nickname, msg_box):
    global chat_msgs
    last_idx = len(chat_msgs)

    while True:
        await asyncio.sleep(1)
        
        for m in chat_msgs[last_idx:]:
            if m[0] != nickname: # if not a message from current user
                if m[1].endswith(('.png', '.jpg', '.jpeg', '.gif')):
                    msg_box.append(put_markdown(f"`{m[0]}`: {put_image(src='data:image/jpeg;base64,'+m[2], width='170px')}"))
                else:
                    msg_box.append(put_markdown(f"`{m[0]}`: {m[1]}"))
        
        # remove expired
        if len(chat_msgs) > MAX_MESSAGES_COUNT:
            chat_msgs = chat_msgs[len(chat_msgs) // 2:]
        
        last_idx = len(chat_msgs)

if __name__ == "__main__":
    start_server(main, debug=True, port=8080, cdn=True, static_dir='./static')

