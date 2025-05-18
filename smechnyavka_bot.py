import asyncio
import json
import aiohttp

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from config import TOKEN

global bot
dp = Dispatcher()

answers = {}
groups_count = 0

class Form(StatesGroup):
    get_nickname = State()
    wait_for_answer = State()
    voting = State()
    ended = State()



@dp.message(Command("start"))
async def command_start_handler(message: Message, state: FSMContext) -> None:

    await message.answer("Введите свой никнейм: ")
    await state.set_state(Form.get_nickname)

@dp.message(Form.get_nickname)
async def process_nickname(message: Message, state: FSMContext) -> None:
    global groups_count

    await send_user_info(message.chat.id, message.text)
    await message.answer(f"{message.text}, вы в лобби. Ожидайте начала игры.")
    await process_question(message.chat.id, state)
    
    groups_count = await get_groups_count()

@dp.message(Form.wait_for_answer)
async def process_answer(message: Message, state: FSMContext) -> None:
    answer = message.text
    await send_user_answer(message.chat.id, answer)
    await message.answer(f"Ваш ответ записан. Ожидаем других игроков.")

    await send_answers_to_user(message.chat.id, state)

    

@dp.message(Form.voting)
async def process_answer(message: Message, state: FSMContext) -> None:
    global groups_count

    if(message.text == "#1"):
        await send_vote(message.chat.id, answers["answer1"]["user_id"])
    elif(message.text == "#2"):
        await send_vote(message.chat.id, answers["answer2"]["user_id"])

    if(groups_count > 0):
        await send_answers_to_user(message.chat.id, state)
    else:
        await message.answer("Игра закончена!")
        await state.set_state(Form.ended)



async def process_question(user_id: int, state: FSMContext) -> None:
    question = await get_question(user_id)
    await bot.send_message(user_id, question)
    await state.set_state(Form.wait_for_answer)

async def get_question(user_id: int) -> str:
    url = f"https://unit-hack-2025.onrender.com/game/api/prompt?telegram_id={user_id}"

    async with aiohttp.ClientSession() as session:
        response = await session.get(url)
        json = await response.json()
        print(f"При получении вопроса для пользователя {user_id} получили код {response.status}")

    return json["prompt"]

async def get_groups_count() -> int:
    url = f"https://unit-hack-2025.onrender.com/game/api/count/"

    async with aiohttp.ClientSession() as session:
        response = await session.get(url)
        json = await response.json()
        print(f"При получении количества групп получили код {response.status}")

    return json["count"]

async def get_answers() -> dict:
    global groups_count
    global answers

    url = f"https://unit-hack-2025.onrender.com/game/api/answer/"

    async with aiohttp.ClientSession() as session:
        response = await session.get(url)
        answers = await response.json()
        print(f"При получении пары ответов получили код {response.status}")

    return answers
  
    

async def send_answers_to_user(user_id: int, state: FSMContext):
    global answers 
    answers = await get_answers()

    first_button = KeyboardButton(text="#1")
    second_button = KeyboardButton(text="#2")
    keyboard = ReplyKeyboardMarkup(keyboard=[[first_button, second_button]],resize_keyboard=True)

    await bot.send_message(user_id, text="Вопрос: " + answers["question"])
    await bot.send_message(user_id, f"Ответ 1 от {answers["answer1"]["username"]}: {answers["answer1"]["answer"]}")
    await bot.send_message(user_id, f"Ответ 2 от {answers["answer2"]["username"]}: {answers["answer2"]["answer"]}", reply_markup=keyboard)

    await state.set_state(Form.voting)    

async def send_user_info(user_id: int, username: str) -> None:
    url = "https://unit-hack-2025.onrender.com/game/api/connect/"
    headers = {'Content-Type' : 'application/json'}
    data = {"telegram_id" : user_id, "username" : username}

    async with aiohttp.ClientSession() as session:
        response = await session.post(url=url, data= json.dumps(data), headers=headers)
        print(f"При отправке данных пользователя {user_id} пришёл код: {response.status}")

async def send_user_answer(user_id: int, answer: str) -> None:
    url = "https://unit-hack-2025.onrender.com/game/api/answer/"
    headers = {'Content-Type' : 'application/json'}
    data = {"telegram_id" : user_id, "answer" : answer}

    async with aiohttp.ClientSession() as session:
        response = await session.post(url=url, data= json.dumps(data), headers=headers)
        print(f"При отправке ответа пользователя {user_id} пришёл код: {response.status}")

async def send_vote(voter_id: int, candidate_id: int) -> None:
    url = "https://unit-hack-2025.onrender.com/game/api/vote/"
    headers = {'Content-Type' : 'application/json'}
    data = {"voter_id" : voter_id, "candidate_id" : candidate_id}

    async with aiohttp.ClientSession() as session:
        response = await session.post(url=url, data= json.dumps(data), headers=headers)
        print(f"При отправке голоса пользователя {voter_id} пришёл код: {response.status}")


# Run the bot
async def main() -> None:
    global bot
    bot = Bot(token=TOKEN)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
          