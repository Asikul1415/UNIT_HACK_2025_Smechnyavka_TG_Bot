import asyncio
import websockets
import json

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from config import TOKEN

global websocket
bot = Bot(token=TOKEN)
dp = Dispatcher()

event_loop = asyncio.get_event_loop()

answers = {}

class Form(StatesGroup):
    get_nickname = State()
    get_prompt_answer = State()
    voting = State()
    already_voted = State()
    ended = State()



@dp.message(Command("start"))
async def command_start_handler(message: Message, state: FSMContext) -> None:
    await message.answer("Введите свой никнейм: ")
    await state.set_state(Form.get_nickname)

@dp.message(Form.get_nickname)
async def process_nickname(message: Message, state: FSMContext) -> None:
    await send_user_info(message.chat.id, message.text)
    await message.answer(f"{message.text}, вы в лобби. Ожидайте начала игры.")
    
    await get_questions()
    await state.set_state(Form.get_prompt_answer)

@dp.message(Form.get_prompt_answer)
async def process_prompt_answer(message: Message, state: FSMContext) -> None:
    await send_user_answer(message.chat.id, message.text)
    await message.answer(f"Ваш ответ записан. Ожидаем других игроков.")

    await send_answers_to_user(message.chat.id, state)

@dp.message(Form.voting)
async def process_vote(message: Message, state: FSMContext) -> None:
    groups_count = await get_groups_count()
    await state.set_state(Form.already_voted)

    if(message.chat.id == answers["answer0"]["telegram_id"] or message.chat.id == answers["answer1"]["telegram_id"]):
        await message.reply("Вы не можете голосовать. Люди судят ваш ответ.")
        return
    
    if(message.text == "#1"):
        await send_vote(message.chat.id, answers["answer0"]["telegram_id"])
    elif(message.text == "#2"):
        await send_vote(message.chat.id, answers["answer1"]["telegram_id"])

    #In progress
    if(groups_count > 0):
        await send_answers_to_user(message.chat.id, state)
    else:
        await message.answer("Игра закончена!")
        await state.set_state(Form.ended)

@dp.message(Form.already_voted)
async def process_trying_to_vote_again(message: Message, state: FSMContext) -> None:
    message.reply("Вы уже голосовали!")
    await send_answers_to_user(message.chat.id, state)



async def get_questions() -> None:
    response = await websocket.recv()
    await handle_responses(response=response)

#In progress
async def get_groups_count() -> int:
    return 0

async def get_answers() -> None:
    response = await websocket.recv()
    await handle_responses(response=response)
  
    

async def send_answers_to_user(user_id: int, state: FSMContext):
    await get_answers()

    first_button = KeyboardButton(text="#1")
    second_button = KeyboardButton(text="#2")
    keyboard = ReplyKeyboardMarkup(keyboard=[[first_button, second_button]],resize_keyboard=True)

    await bot.send_message(user_id, text="Вопрос: " + answers["prompt"])
    await bot.send_message(user_id, f"Ответ 1: {answers["answer0"]["answer"]}")
    await bot.send_message(user_id, f"Ответ 2: {answers["answer1"]["answer"]}", reply_markup=keyboard)   
    await state.set_state(Form.voting)

async def send_user_info(user_id: int, username: str) -> None:
    data = {"type": "register_player", "telegram_id" : user_id, "username" : username}

    await websocket.send(json.dumps(data))
    response = await websocket.recv()

    print(f"При отправке данных пользователя {user_id} пришёл ответ: {response}")

async def send_user_answer(user_id: int, answer: str) -> None:
    data = {"type": "send_player_answer", "telegram_id" : user_id, "answer" : answer}

    await websocket.send(json.dumps(data))
    response = await websocket.recv()

    print(f"При отправке ответа пользователя {user_id} пришёл ответ: {response}")

async def send_vote(voter_id: int, candidate_id: int) -> None:
    data = {"voter_id" : voter_id, "candidate_id" : candidate_id}

    await websocket.send(json.dumps(data))
    response = await websocket.recv()

    print(f"При отправке голоса пользователя {voter_id} пришёл ответ: {response}")



async def handle_responses(response: websockets.Data):
    response = json.loads(response)
    print(f'Получен ответ: {response}')

    if('type' in response.keys() and response['type'] == 'receive_players_prompts'):
        players = response['players']

        for player in players:
            await bot.send_message(player['telegram_id'], player['prompt'])
            print(f'Отправлен вопрос {player['prompt']} для {player['telegram_id']}')   
    elif('type' in response.keys() and response['type'] == 'receive_player_answers'):
        global answers
        answers = response
        print(f'Получена пара ответов {answers}')
    elif('status' in response.keys()):
        print(f'Получен статус {response['status']}')
        


async def connect_to_server():
    global websocket
    websocket = await websockets.connect("wss://unit-hack-2025.onrender.com/ws/bot/")

    await websocket.send("Подключение")
    response = await websocket.recv()
    print(f"Успешное подключение к серверу. Ответ сервера: {response}")

async def start_bot():
    asyncio.get_event_loop().create_task(dp.start_polling(bot))


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(connect_to_server())
    asyncio.get_event_loop().run_until_complete(start_bot())
    asyncio.get_event_loop().run_forever()
          