import asyncio
import json
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# --- НАСТРОЙКИ ---
API_TOKEN = '8863731520:AAFluGQ3Y77nTFZ0aoNfxWGsUP_tVp2_w8M'
ADMIN_ID = 5686387618 
DATA_FILE = "profiles.json"
vips = {5686387618} # Сюда будешь добавлять ID тех, кто купил VIP

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- ЛОГИКА БАЗЫ ДАННЫХ ---
def load_profiles():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return []
    return []

def save_profiles(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

profiles = load_profiles()

# --- СОСТОЯНИЯ (FSM) ---
class ProfileForm(StatesGroup):
    cups = State()
    rank = State()
    primes = State()
    main_hero = State()

class AnonChat(StatesGroup):
    target_id = State()
    message_text = State()

class SupportState(StatesGroup):
    message = State()

# --- КЛАВИАТУРЫ ---
def get_main_menu():
    buttons = [
        [KeyboardButton(text="📝 Создать анкету"), KeyboardButton(text="👥 Искать напарников")],
        [KeyboardButton(text="📊 Мой профиль"), KeyboardButton(text="💎 VIP Статус")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_ranks_kb():
    ranks = ["Бронза", "Серебро", "Золото", "Алмаз", "Мифик", "Легенда", "Мастера"]
    builder = InlineKeyboardBuilder()
    for rank in ranks:
        builder.add(InlineKeyboardButton(text=rank, callback_data=f"rank_{rank}"))
    builder.adjust(2)
    return builder.as_markup()

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def format_profile(p):
    status = "⭐ [VIP БОЕЦ]" if p['id'] in vips else "👤 Игрок"
    frame = "🌟🌟🌟🌟🌟" if p['id'] in vips else "──────────"
    return (
        f"{frame}\n"
        f"**{status}**\n"
        f"🏆 Кубки: `{p['cups']}`\n"
        f"🎖 Ранг: `{p['rank']}`\n"
        f"💎 Праймы/Титулы: `{p['primes']}`\n"
        f"🔫 Мейн: **{p['main']}**\n"
        f"{frame}"
    )

# --- ХЕНДЛЕРЫ ---

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    welcome_text = (
        f"👋 **Привет, {message.from_user.first_name}! Добро пожаловать в BrawlMate!**\n\n"
        "Надоело сливать катки с рандомами? 😤 Здесь ты найдешь тиммейтов, "
        "которые знают, что такое контроль карты и грамотный пик.\n\n"
        "🚀 **Твои возможности:**\n"
        "└ 🔍 Поиск игроков по кубкам и рангу\n"
        "└ 💬 Полностью анонимное общение\n"
        "└ 🏆 Пуш рангов в топовых командах\n\n"
        "Чтобы тебя начали искать, нажми кнопку **📝 Создать анкету**!"
    )
    await message.answer(welcome_text, reply_markup=get_main_menu(), parse_mode="Markdown")

@dp.message(F.text == "📊 Мой профиль")
async def my_profile(message: types.Message):
    user_id = message.from_user.id
    profile = next((p for p in profiles if p['id'] == user_id), None)
    
    if not profile:
        return await message.answer("⚠️ У тебя еще нет анкеты! Создай её, чтобы начать поиск.")
    
    await message.answer(f"Твоя текущая анкета:\n\n{format_profile(profile)}", parse_mode="Markdown")

# --- ПРОЦЕСС СОЗДАНИЯ АНКЕТЫ ---
@dp.message(F.text == "📝 Создать анкету")
async def start_form(message: types.Message, state: FSMContext):
    await message.answer("Сколько у тебя всего кубков? (Введи только число)")
    await state.set_state(ProfileForm.cups)

@dp.message(ProfileForm.cups)
async def process_cups(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("Пожалуйста, введи число кубков цифрами!")
    await state.update_data(cups=message.text)
    await message.answer("Какой твой максимальный ранг в лиге?", reply_markup=get_ranks_kb())
    await state.set_state(ProfileForm.rank)

@dp.callback_query(F.data.startswith("rank_"), ProfileForm.rank)
async def process_rank(callback: types.CallbackQuery, state: FSMContext):
    rank_val = callback.data.split("_")[1]
    await state.update_data(rank=rank_val)
    await callback.message.answer("Сколько у тебя праймов?")
    await state.set_state(ProfileForm.primes)

@dp.message(ProfileForm.primes)
async def process_primes(message: types.Message, state: FSMContext):
    await state.update_data(primes=message.text)
    await message.answer("На ком ты играешь лучше всего (твой Мейн)?")
    await state.set_state(ProfileForm.main_hero)

@dp.message(ProfileForm.main_hero)
async def process_main(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = message.from_user.id
    
    global profiles
    profiles = [p for p in profiles if p['id'] != user_id]
    
    new_profile = {
        "id": user_id,
        "cups": data['cups'],
        "rank": data['rank'],
        "primes": data['primes'],
        "main": message.text
    }
    profiles.append(new_profile)
    save_profiles(profiles)
    
    await message.answer("✅ **Анкета успешно сохранена!**\nТеперь другие игроки смогут предложить тебе игру.", reply_markup=get_main_menu(), parse_mode="Markdown")
    await state.clear()

# --- ПОИСК И ЧАТ ---
@dp.message(F.text == "👥 Искать напарников")
async def search_profiles(message: types.Message):
    if not profiles:
        return await message.answer("База пуста! Стань первым, кто создаст анкету.")
    
    # Сортируем: сначала VIP-ы (те, кто в списке vips)
    sorted_profiles = sorted(profiles, key=lambda x: x['id'] in vips, reverse=True)
    
    for p in sorted_profiles[:5]: # Показываем последние 5
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💬 Написать анонимно", callback_data=f"chat_{p['id']}")]
        ])
        await message.answer(format_profile(p), reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("chat_"))
async def start_chat(callback: types.CallbackQuery, state: FSMContext):
    target_id = int(callback.data.split("_")[1])
    if target_id == callback.from_user.id:
        return await callback.answer("Это твоя собственная анкета! 😊", show_alert=True)
    
    await state.update_data(target_id=target_id)
    await callback.message.answer("Введите сообщение для игрока. Оно будет отправлено анонимно:")
    await state.set_state(AnonChat.message_text)

@dp.message(AnonChat.message_text)
async def forward_anon_msg(message: types.Message, state: FSMContext):
    data = await state.get_data()
    target_id = data['target_id']
    
    try:
        reply_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="↩️ Ответить анонимно", callback_data=f"chat_{message.from_user.id}")]
        ])
        await bot.send_message(target_id, f"📩 **Новое анонимное сообщение:**\n\n{message.text}", reply_markup=reply_kb, parse_mode="Markdown")
        await message.answer("✅ Твое сообщение доставлено!")
    except:
        await message.answer("❌ Ошибка: пользователь заблокировал бота или удалил аккаунт.")
    await state.clear()

# --- VIP СТАТУС ---
@dp.message(F.text == "💎 VIP Статус")
async def vip_menu(message: types.Message):
    vip_text = (
        "⭐ **ПРЕИМУЩЕСТВА VIP-СТАТУСА** ⭐\n\n"
        "Хочешь найти профи-команду быстрее всех? VIP дает тебе:\n\n"
        "1️⃣ **Топ-позиция:** Твоя анкета всегда первая в списке поиска.\n"
        "2️⃣ **Элитный дизайн:** Золотая рамка и значок ⭐ выделяют тебя среди других.\n"
        "3️⃣ **Доверие:** Игроки охотнее пишут VIP-пользователям.\n"
        "4️⃣ **Поддержка:** Ты помогаешь нашему проекту развиваться!\n\n"
        "💰 **Стоимость: 0.5 TON (~150₽)**\n"
        "Оплата принимается через @Wallet (крипто-чек или перевод)."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Купить VIP (Написать админу)", callback_data="ask_admin")]
    ])
    await message.answer(vip_text, reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data == "ask_admin")
async def contact_admin(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Напиши сообщение админу (например, 'хочу купить вип'). Он свяжется с тобой для оплаты.")
    await state.set_state(SupportState.message)

@dp.message(SupportState.message)
async def forward_to_admin(message: types.Message, state: FSMContext):
    await bot.send_message(ADMIN_ID, f"🆕 **ЗАЯВКА НА VIP!**\nЮзер: `{message.from_user.id}`\nТекст: {message.text}", parse_mode="Markdown")
    await message.answer("✅ Заявка отправлена! Админ скоро напишет тебе.")
    await state.clear()

# --- ЗАПУСК ---
async def main():
    print("Бот BrawlMate успешно запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())