from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, ReplyKeyboardRemove, InputFile
from time import time
from os.path import isfile
from json import load, dump
from aiogram.contrib.fsm_storage.memory import MemoryStorage

import sqlite3 as sl
con = sl.connect('thecod.db')


import settings

TOKEN = settings.API_KEY

bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
database = []


class Main(StatesGroup):
    Wait_for_action = State()
    Wait_for_name = State()
    Wait_for_article = State()
    Wait_for_photo = State()
    Wait_for_searching_action = State()
    Wait_for_searching_name = State()
    Wait_for_searching_article = State()


@dp.message_handler(commands=['start'])
async def parrot(msg: types.Message, state: FSMContext):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add('Добавить')
    keyboard.add('Посмотреть')
    await state.set_state(Main.Wait_for_action.state)
    await msg.answer(f'Выберите действие', reply_markup=keyboard)


@dp.message_handler(state=Main.Wait_for_action)
async def wait_for_action(msg: types.Message, state: FSMContext):
    if msg.text == 'Добавить':
        await state.set_state(Main.Wait_for_name.state)
        await msg.answer(f'Напишите название оборудования', reply_markup=ReplyKeyboardRemove())
    elif msg.text == 'Посмотреть':
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add('Найти по названию')
        keyboard.add('Найти по артикулу')
        await state.set_state(Main.Wait_for_searching_action.state)
        await msg.answer('Выберите тип поиска', reply_markup=keyboard)
    else:
        await msg.answer('Пожалуйста, воспользуйтесь кнопками')


@dp.message_handler(state=Main.Wait_for_searching_action)
async def wait_for_searching_action(msg: types.Message, state: FSMContext):
    if msg.text == 'Найти по названию':
        await msg.answer('Введите название оборудования', reply_markup=ReplyKeyboardRemove())
        await state.set_state(Main.Wait_for_searching_name.state)
    elif msg.text == 'Найти по артикулу':
        await msg.answer('Введите артикул оборудования', reply_markup=ReplyKeyboardRemove())
        await state.set_state(Main.Wait_for_searching_article.state)
    else:
        await msg.answer('Пожалуйста, воспользуйтесь кнопками')


async def show(msg: types.Message, name, article):
    if article == 'None':
        result = [el for el in database if name == el['name']]
    else:
        result = [el for el in database if name == el['name'] and article == el['article']]
    for el in result:
        await bot.send_photo(
            msg.chat.id,
            InputFile(result[0]['photo']),
            f'Название: {result[0]["name"]}\nАртикул: {result[0]["article"]}'
        )


@dp.message_handler(state=Main.Wait_for_searching_name)
async def wait_for_searching_name(msg: types.Message, state: FSMContext):
    if len(msg.text.lower().split(' / ')) == 2:
        name, article = msg.text.split(' / ')
        await state.set_state(Main.Wait_for_action.state)
        await show(msg, name, article)
        await parrot(msg, state)
        return
    result = [el for el in database if msg.text.lower() in el['name'].lower()]
    if not result:
        await msg.answer('Не найдено. Попробуйте еще раз')
        return
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    for el in result:
        keyboard.add(f'{el["name"]} / {el["article"]}')
    await msg.answer('Выберите варианты', reply_markup=keyboard)


@dp.message_handler(state=Main.Wait_for_searching_article)
async def wait_for_searching_article(msg: types.Message, state: FSMContext):
    if len(msg.text.lower().split(' / ')) == 2:
        name, article = msg.text.split(' / ')
        await state.set_state(Main.Wait_for_action.state)
        await show(msg, name, article)
        await parrot(msg, state)
        return
    result = [el for el in database if el['article'] and msg.text.lower() in el['article'].lower()]
    if not result:
        await msg.answer('Не найдено. Попробуйте еще раз')
        return
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    for el in result:
        keyboard.add(f'{el["name"]} / {el["article"]}')
    await msg.answer('Выберите варианты', reply_markup=keyboard)


@dp.message_handler(state=Main.Wait_for_name)
async def wait_for_name(msg: types.Message, state: FSMContext):
    await msg.answer(f'Оборудование: {msg.text}')
    await state.update_data(name=msg.text)
    await state.set_state(Main.Wait_for_article.state)
    keyboard = ReplyKeyboardMarkup()
    keyboard.add('Нет артикула')
    await msg.answer(f'Введите артикул', reply_markup=keyboard)


@dp.message_handler(state=Main.Wait_for_article)
async def wait_for_article(msg: types.Message, state: FSMContext):
    if msg.text == 'Нет артикула':
        pass
    else:
        await state.update_data(article=msg.text)
    await msg.answer('Прикрепите фото', reply_markup=ReplyKeyboardRemove())
    await state.set_state(Main.Wait_for_photo.state)


@dp.message_handler(content_types=['photo'], state=Main.Wait_for_photo)
async def photo(msg: types.Message, state: FSMContext):
    photo_path = f'upload/{msg.chat.id}/{time()}.jpg'
    await msg.photo[-1].download(destination_file=photo_path)
    data = await state.get_data()
    if 'article' not in data.keys():
        data['article'] = None
    database.append(
        {
            'name': data['name'],
            'article': data['article'],
            'photo': photo_path
        }
    )
    with open('db.json', 'w') as f:
        dump(database, f)
    await msg.answer('Фото сохранено')
    await parrot(msg, state)


if __name__ == '__main__':
    if isfile('db.json'):
        with open('db.json', 'r') as f:
            database = load(f)
    executor.start_polling(dp, skip_updates=True)
