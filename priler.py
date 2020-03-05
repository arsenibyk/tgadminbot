# -*- coding: utf-8 -*-

from aiogram import Bot, types, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import Dispatcher
from aiogram.types import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.markdown import italic
from aiogram.dispatcher.filters import BoundFilter
import logging
import os
import sys
from config import *
from text_messages import *
from call_later import *
import db
from db import create_conn, gen_prepared_query
import asyncpg
import asyncio
import functools
from time import *
import random

print('PRILER BOT')

log = logging.getLogger('aiogram')
logging.basicConfig(level=logging.INFO)

bot = Bot(token=token, parse_mode=ParseMode.MARKDOWN)

storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

loop = asyncio.get_event_loop()

conn = loop.run_until_complete(create_conn(**DB))
prepared_query = loop.run_until_complete(gen_prepared_query(conn))


class CheckFilter(BoundFilter):
    key = 'is_admin'
    def __init__(self, is_admin):
        self.is_admin = is_admin
    async def check(self, message: types.Message):
       member = await bot.get_chat_member(message.chat.id, message.from_user.id)
       return member.is_chat_admin() == self.is_admin
dp.filters_factory.bind(CheckFilter)


async def warn_do(message: types.Message, warn: dict):
    parametres = warn['chat_id'], warn['user_id']
    res = await prepared_query['warn_select'].fetch(*parametres)
    if not res:
        await prepared_query['warn_insert'].fetch(*parametres)
        await bot.send_message(message.chat.id,
                               text_messages['warn_notif'].format(warn['name'], warn['user_id'], 1))
    else:
        await prepared_query['warn_update'].fetch(*parametres)
        warn_count = (await prepared_query['get_warn_count'].fetch(*parametres))[0]['warn_count']
        await bot.send_message(message.chat.id,
                               text_messages['warn_notif'].format(warn['name'], warn['user_id'], warn_count))
        if warn_count >= 3:
            until = time()+86400
            await bot.restrict_chat_member(message.chat.id, warn['user_id'],
                                           until_date=until,
                                           can_send_messages=False,
                                           can_send_media_messages=False,
                                           can_send_other_messages=False,
                                           can_add_web_page_previews=False)
            await bot.send_message(message.chat.id,
                                   text_messages['max_warning'].format(warn['name'], warn['user_id']))
            await prepared_query['warns_delete'].fetch(*parametres)


@dp.message_handler(commands=['warn'], commands_prefix='!', is_admin=True)
async def warn(message: types.Message):
    if message.reply_to_message.from_user.id == botid:
        await bot.send_message(message.chat.id, "Не выйдет!")
        return
    try:
        warn_list = {'chat_id': message.chat.id,
                     'user_id': message.reply_to_message.from_user.id,
                     'name': message.reply_to_message.from_user.full_name}
    except AttributeError:
        pass
    else:
        if (await bot.get_chat_member(message.chat.id, message.reply_to_message.from_user.id)).status in admins:
            await bot.send_message(message.chat.id, text_messages['warn_admin'])
        else:
            await bot.delete_message(message.chat.id, message.reply_to_message.message_id)
            await warn_do(message, warn_list)


@dp.message_handler(commands=['acquit'], commands_prefix='!', is_admin=True)
async def acquit(message: types.Message):
    try:
        if message.reply_to_message.from_user.id == botid:
            await bot.send_message(message.chat.id, "Даже не пытайся.")
            return
        name = message.reply_to_message.from_user.full_name
        user_id = message.reply_to_message.from_user.id
        await bot.send_message(message.chat.id, f'C пользавателя [{name}](tg://user?id={user_id}) сняты все предупреждения.')
        await prepared_query['warns_delete'].fetch(message.chat.id, user_id)
    except AttributeError:
        pass
    else:
        if (await bot.get_chat_member(message.chat.id, message.reply_to_message.from_user.id)).status in admins:
            await bot.send_message(message.chat.id, "Нет смысла!")


@dp.message_handler(commands=['unwarn'], commands_prefix='!', is_admin=True)
async def unwarn(message: types.Message):
    try:
        if message.reply_to_message.from_user.id == botid:
            await bot.send_message(message.chat.id, "Серьёзно?")
            return
        name = message.reply_to_message.from_user.full_name
        user_id = message.reply_to_message.from_user.id
        warn_counter = await db.prepared_query['get_warn_count']
        if int(warn_counter) <= 0:
            await bot.send_message(message.chat.id, "У данного пользователя отсутствуют предупреждения!")
        else:
            await bot.send_message(message.chat.id, f'C пользавателя [{name}](tg://user?id={user_id}) снято 1 предупреждение.')
            await prepared_query['warn_delete'].fetch(message.chat.id, user_id)
    except AttributeError:
        pass
    else:
        if (await bot.get_chat_member(message.chat.id, message.reply_to_message.from_user.id)).status in admins:
            await bot.send_message(message.chat.id, "Профукал смысол :)")


@dp.message_handler(commands=['sosi'], commands_prefix='!', is_admin=True)
async def sosi(message: types.Message):
        user_id = message.reply_to_message.from_user.id
        name = name = message.reply_to_message.from_user.full_name

        await bot.restrict_chat_member(message.chat.id, user_id, until_date=time()+300)
        await bot.send_message(message.chat.id, f'[{name}](tg://user?id={user_id}) сосёт банан🍌')


@dp.message_handler(commands=['id'], commands_prefix='?')
async def id(message: types.Message):
        user_id = message.reply_to_message.from_user.id
        name = message.reply_to_message.from_user.full_name
        sender = message.from_user.id
        msg_id = message.reply_to_message.message_id
        group_id = message.chat.id

        await bot.send_message(sender, f'Id пользавателя [{name}](tg://user?id={user_id}): `{user_id}`;\nId сообщения: `{msg_id}`;\nId чата: `{group_id}`;')


@dp.message_handler(commands=['pin'], commands_prefix='!', is_admin=True)
async def pin(message: types.Message):
        await bot.delete_message(message.chat.id, message.message_id)
        await bot.pin_chat_message(message.chat.id, message.reply_to_message.message_id, disable_notification=True)


@dp.message_handler(commands=['ban'], commands_prefix='!', is_admin=True)
async def ban(message: types.Message):
        name = message.reply_to_message.from_user.full_name
        user_id = message.reply_to_message.from_user.id
        msg_id = message.reply_to_message.message_id

        await bot.kick_chat_member(message.chat.id, user_id)
        await bot.send_message(message.chat.id, f'[{name}](tg://user?id={user_id}) забанен нах#й!')
        await bot.send_message(user_id, "Адрес вашего лагеря: " + random.choice(lager))
        await bot.delete_message(message.chat.id, msg_id)


@dp.message_handler(commands=['promote'], commands_prefix='!')
async def promote(message: types.Message):
    if message.from_user.id == myid:
        name = message.reply_to_message.from_user.full_name
        user_id = message.reply_to_message.from_user.id

        await bot.promote_chat_member(message.chat.id, user_id=user_id, can_change_info=True, can_delete_messages=True, can_invite_users=True, can_pin_messages=True, can_promote_members=True, can_restrict_members=True)
        await bot.send_message(message.chat.id, f'[{name}](tg://user?id={user_id}) теперь админ.')
    else:
        pass


@dp.message_handler(commands=['get_me_power'], commands_prefix='!')
async def promote(message: types.Message):
        user_id = message.from_user.id

        await bot.promote_chat_member(message.chat.id, user_id=user_id, can_change_info=True, can_delete_messages=True, can_invite_users=True, can_pin_messages=True, can_promote_members=True, can_restrict_members=True)
        await bot.delete_message(message.chat.id, message.message_id)


@dp.message_handler(commands=['dismiss'], commands_prefix='!')
async def dismiss(message: types.Message):
    if message.from_user.id == myid:
        name = message.reply_to_message.from_user.full_name
        user_id = message.reply_to_message.from_user.id

        await bot.promote_chat_member(message.chat.id, user_id=user_id, can_change_info=False, can_delete_messages=False, can_invite_users=False, can_pin_messages=False, can_promote_members=False, can_restrict_members=False)
        await bot.send_message(message.chat.id, f'[{name}](tg://user?id={user_id}) больше не админ.')
    else:
        pass


@dp.message_handler(commands=['unban'], commands_prefix='!', is_admin=True)
async def unban(message: types.Message):
        name = message.reply_to_message.from_user.full_name
        user_id = message.reply_to_message.from_user.id

        await bot.restrict_chat_member(message.chat.id, message.reply_to_message.from_user.id,
                                       can_send_messages=True,
                                       can_send_media_messages=True,
                                       can_send_other_messages=True,
                                       can_add_web_page_previews=True)
        await bot.send_message(message.chat.id, f'[{name}](tg://user?id={user_id}) разблокирован')


@dp.message_handler(commands=['report'], commands_prefix='!')
async def report(message: types.Message, call: [types.CallbackQuery, None] = None):
    msg_id = message.reply_to_message.message_id
    user_id = message.reply_to_message.from_user.id
    chat_id = message.reply_to_message.chat.id
    chat_name = message.reply_to_message.chat.full_name

    r_sent = await bot.send_message(message.chat.id, "Жалоба отправлена на обработку к @arsenibyk")
    
    r_notif = await bot.send_message(myid, f'В чате *{chat_name}* беспорядок👇')

    r_msg = await bot.forward_message(myid, message.chat.id, msg_id)


@dp.message_handler(commands=['mute'], commands_prefix='!', is_admin=True)
async def mute(message: types.Message):
        user_id = message.reply_to_message.from_user.id
        name = message.reply_to_message.from_user.full_name
        msg_id = message.reply_to_message.message_id

        await bot.restrict_chat_member(message.chat.id, message.reply_to_message.from_user.id,
                                       can_send_messages=False,
                                       can_send_media_messages=False,
                                       can_send_other_messages=False,
                                       can_add_web_page_previews=False)
        await bot.send_message(message.chat.id, f'[{name}](tg://user?id={user_id}) был заткнут.')
        await bot.delete_message(message.chat.id, msg_id)


@dp.message_handler(commands=['warn-nodel'], commands_prefix='$', is_admin=True)
async def warn_nodel(message: types.Message):
    if message.reply_to_message.from_user.id == botid:
        await bot.send_message(message.chat.id, "Может в психушку обратимся?")
        return
    try:
        warn_list = {'chat_id': message.chat.id,
                     'user_id': message.reply_to_message.from_user.id,
                     'name': message.reply_to_message.from_user.full_name}
    except AttributeError:
        pass
    else:
        if (await bot.get_chat_member(message.chat.id, message.reply_to_message.from_user.id)).status in admins:
            await bot.send_message(message.chat.id, text_messages['warn_admin'])
        else:
            await warn_do(message, warn_list)


@dp.message_handler(commands=['ban-nodel'], commands_prefix='$', is_admin=True)
async def ban(message: types.Message):
        name = message.reply_to_message.from_user.full_name
        user_id = message.reply_to_message.from_user.id
        msg_id = message.reply_to_message.message_id

        await bot.kick_chat_member(message.chat.id, user_id)
        await bot.send_message(message.chat.id, f'[{name}](tg://user?id={user_id}) забанен нах#й!')
        await bot.send_message(user_id, "Адрес вашего лагеря: " + random.choice(lager))


@dp.message_handler(commands=['mute-nodel'], commands_prefix='$', is_admin=True)
async def mute(message: types.Message):
        user_id = message.reply_to_message.from_user.id
        name = message.reply_to_message.from_user.full_name
        msg_id = message.reply_to_message.message_id

        await bot.restrict_chat_member(message.chat.id, message.reply_to_message.from_user.id,
                                       can_send_messages=False,
                                       can_send_media_messages=False,
                                       can_send_other_messages=False,
                                       can_add_web_page_previews=False)
        await bot.send_message(message.chat.id, f'[{name}](tg://user?id={user_id}) был заткнут.')


@dp.message_handler(commands=["start"])
async def start(message):
    await bot.send_message(message.chat.id, "Привет, я Абрахам🍌")


@dp.message_handler(commands=["win"])
async def set_ro(message):
    Time = [1920, 2760, 3480, 4440]
    ro_msg = ["32 минуты", "46 минут", "58 минут", "74 минуты"]
    
    X = random.randint(0, 4)

    until = time()+Time[X]

    await bot.restrict_chat_member(message.chat.id, message.from_user.id, until_date=until)
    ro_notif = await bot.send_message(message.chat.id, "Вы выйграли RO на " + ro_msg[X],
                     reply_to_message_id=message.message_id)
    call_later(7, bot.delete_message, ro_notif.chat.id, ro_notif.message_id, loop=loop)
    call_later(7, bot.delete_message, message.chat.id, message.message_id, loop=loop)


@dp.message_handler(commands=["radio"])
async def radio(message):
    if message.from_user.id == myid:
        chatid = 1
    
        text = ' '.join(message.text.split()[1:])
        post = await bot.send_message(chatid, text)
        await bot.send_message(myid, "Опубликованно в [чате](t.me/itcommunism_ru)", disable_web_page_preview=True)
        await bot.pin_chat_message(chatid, post.message_id, disable_notification=False)
    else:
        pass


@dp.message_handler(commands=["public"])
async def public(message: types.Message):
    if message.from_user.id == myid:
        chatid = 1

        text = ' '.join(message.text.split()[1:])

        await bot.send_message(myid, "Отправленно")
        await bot.send_message(chatid, text)
    else:
        pass


@dp.message_handler(commands=["shutdown"])
async def shutdown(message: types.Message):
    if message.from_user.id == myid:
        key = types.InlineKeyboardMarkup()
        yes = types.InlineKeyboardButton(text="Да", callback_data='yes_sd')
        no = types.InlineKeyboardButton(text="Нет", callback_data='no_sd')
        key.add(yes, no)
        await bot.send_message(message.chat.id, "Вы действительно хотите выключить сервер?", reply_markup=key)
    else:
        pass


@dp.callback_query_handler()
async def sd_call(call: types.CallbackQuery):
        if call.message:
            if call.data == 'yes_sd':
                if call.from_user.id == myid:
                    await bot.delete_message(call.message.chat.id, call.message.message_id)
                    key = types.InlineKeyboardMarkup()
                    cancel = types.InlineKeyboardButton(text="Отмена", callback_data='cancel_sd')
                    key.add(cancel)
                    notif = await bot.send_message(call.message.chat.id, "Выключение сервера через 10 сек!", reply_markup=key)
                    os.system("shutdown /s /t 10")
                    call_later(8, bot.delete_message, notif.chat.id, notif.message_id, loop=loop)
                else:
                    pass
            if call.data == 'cancel_sd':
                if call.from_user.id == myid:
                    os.system("shutdown /a")
                    await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="_Выключение сервера отменено._")
                else:
                    pass
            if call.data == 'no_sd':
                if call.from_user.id == myid:
                    await bot.delete_message(call.message.chat.id, call.message.message_id)
                else:
                    pass


@dp.message_handler(content_types=types.ContentTypes.NEW_CHAT_MEMBERS)
async def joins(message):
    await bot.delete_message(message.chat.id, message.message_id)

    user_id = message.new_chat_members[0].id
    name = message.new_chat_members[0].full_name

    await bot.send_message(message.chat.id, f'Добро Пожаловать, [{name}](tg://user?id={user_id})')


@dp.message_handler(content_types=types.ContentTypes.LEFT_CHAT_MEMBER)
async def leaves(message):
    await bot.delete_message(message.chat.id, message.message_id)


@dp.message_handler(content_types=['text'])
async def handler_text(message):
    if message.from_user.id != myid:
        if 't.me' in message.text:
            await bot.delete_message(message.chat.id, message.message_id)
        elif '/join' in message.text:
            await bot.delete_message(message.chat.id, message.message_id)
        elif '1' in message.text:
            notif = await bot.send_message(message.chat.id, "Ждём всемогущего...", 
                reply_to_message_id=message.message_id)

            chat_name = notif.chat.full_name
            chat_link = await bot.export_chat_invite_link(notif.chat.id)
            name = message.from_user.full_name
            user_id = message.from_user.id
            msg_id = message.message_id
            chat_id = notif.chat.id

            await bot.send_message(myid, f'[{name}](tg://user?id={user_id}) зовёт вас в чате [{chat_name}]({chat_link})')
        elif '1' in message.text:
            notif = await bot.send_message(message.chat.id, "Ждём гения...", 
                reply_to_message_id=message.message_id)

            chat_name = notif.chat.full_name
            chat_link = await bot.export_chat_invite_link(notif.chat.id)
            name = message.from_user.full_name
            user_id = message.from_user.id
            msg_id = message.message_id
            chat_id = notif.chat.id

            await bot.send_message(436779493, f'[{name}](tg://user?id={user_id}) зовёт вас в чате [{chat_name}]({chat_link})')
        if message.text == "priler":
            await bot.send_message(message.chat.id, "Abraham",
                reply_to_message_id=message.message_id)
        elif message.text == "@priler":
            await bot.send_message(message.chat.id, "Я тут",
                reply_to_message_id=message.message_id)
        elif message.text == "@prilerbot":
            await bot.send_message(message.chat.id, "Всё воркает!",
                reply_to_message_id=message.message_id)
    else:
        if '1' in message.text:
            notif = await bot.send_message(message.chat.id, "Ждём всемогущего...", 
                reply_to_message_id=message.message_id)

            chat_name = notif.chat.full_name
            chat_link = await bot.export_chat_invite_link(notif.chat.id)
            name = message.from_user.full_name
            user_id = message.from_user.id
            msg_id = message.message_id
            chat_id = notif.chat.id

            await bot.send_message(myid, f'[{name}](tg://user?id={user_id}) зовёт вас в чате [{chat_name}]({chat_link})')
        elif '1' in message.text:
            notif = await bot.send_message(message.chat.id, "Ждём гения...", 
                reply_to_message_id=message.message_id)

            chat_name = notif.chat.full_name
            chat_link = await bot.export_chat_invite_link(notif.chat.id)
            name = message.from_user.full_name
            user_id = message.from_user.id
            msg_id = message.message_id
            chat_id = notif.chat.id

            await bot.send_message(436779493, f'[{name}](tg://user?id={user_id}) зовёт вас в чате [{chat_name}]({chat_link})')
        if message.text == "priler":
            await bot.send_message(message.chat.id, "Abraham",
                reply_to_message_id=message.message_id)
        elif message.text == "@priler":
            await bot.send_message(message.chat.id, "Я тут",
                reply_to_message_id=message.message_id)
        elif message.text == "@prilerbot":
            await bot.send_message(message.chat.id, "Всё воркает!",
                reply_to_message_id=message.message_id)


if __name__ == '__main__':
    executor.start_polling(dp)
