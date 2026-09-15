from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
import time

from config import ADMIN_ID, LEARNING_DAYS
import database as db

router = Router()

LEARNING_SECONDS = LEARNING_DAYS * 24 * 60 * 60


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Команда /start в группе — показать кнопку."""
    if message.chat.id == message.from_user.id:
        # В личке
        await message.answer("Привет! Добавь меня в группу и напиши /start там.")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎓 Начать обучение", callback_data="start_learning")]
    ])
    await message.answer(
        "Готов к обучению. Нажми кнопку ниже, чтобы начать сбор сообщений на 3 дня.",
        reply_markup=keyboard
    )


@router.callback_query(F.data == "start_learning")
async def on_start_learning(callback: CallbackQuery):
    """Обработка нажатия кнопки. Только админ."""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Нет прав. Только админ может запустить обучение.", show_alert=True)
        return

    status = await db.get_state("learning_status", "idle")
    if status == "collecting":
        await callback.answer("⚠️ Обучение уже идёт.", show_alert=True)
        return
    if status == "ready":
        await callback.answer("✅ Обучение уже завершено.", show_alert=True)
        return

    await db.set_state("learning_status", "collecting")
    await db.set_state("learning_started_at", str(int(time.time())))

    await callback.message.edit_text(
        "🎓 <b>Обучение началось!</b>\n\n"
        f"Бот будет запоминать все сообщения в течение {LEARNING_DAYS} дней. "
        "После этого напишет, что готов."
    )
    await callback.answer("Обучение запущено")


@router.message(F.text | F.sticker | F.animation | F.photo)
async def collect_messages(message: Message):
    """Собирает всё, что пишут в группе, пока идёт обучение."""
    status = await db.get_state("learning_status", "idle")
    if status != "collecting":
        return

    # Текст
    if message.text:
        username = message.from_user.username or message.from_user.first_name or "unknown"
        await db.save_message(message.from_user.id, username, message.text)

    # Стикеры
    if message.sticker:
        await db.save_media(message.sticker.file_id, "sticker")

    # GIF
    if message.animation:
        await db.save_media(message.animation.file_id, "animation")

    # Картинки
    if message.photo:
        await db.save_media(message.photo[-1].file_id, "photo")


async def check_learning_done(bot):
    """Вызывается планировщиком раз в минуту."""
    status = await db.get_state("learning_status", "idle")
    if status != "collecting":
        return

    started_at = int(await db.get_state("learning_started_at", "0"))
    if time.time() - started_at < LEARNING_SECONDS:
        return

    await db.set_state("learning_status", "ready")

    from config import GROUP_ID
    if GROUP_ID:
        try:
            await bot.send_message(
                GROUP_ID,
                "✅ <b>Обучение закончено!</b>\n\nНапишите мне что-то."
            )
        except Exception as e:
            print(f"Не удалось отправить сообщение: {e}")
