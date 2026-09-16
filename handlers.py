from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
import time
import random
import aiosqlite

from config import ADMIN_ID, LEARNING_DAYS, GROUP_ID
import database as db
from ai import generate_reply

router = Router()

LEARNING_SECONDS = LEARNING_DAYS * 24 * 60 * 60


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Команда /start в группе — показать кнопку."""
    if message.chat.id == message.from_user.id:
        await message.answer("Привет! Добавь меня в группу и напиши /start там.")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎓 Начать обучение", callback_data="start_learning")]
    ])
    await message.answer(
        "Готов к обучению. Нажми кнопку ниже, чтобы начать сбор сообщений на 3 дня.",
        reply_markup=keyboard
    )


@router.message(Command("setready"))
async def cmd_setready(message: Message):
    """Админ-команда: вручную завершить обучение и показать статистику."""
    if message.from_user.id != ADMIN_ID:
        return
    await db.set_state("learning_status", "ready")
    status = await db.get_state("learning_status")
    async with aiosqlite.connect(db.DB_PATH) as d:
        msgs = (await (await d.execute("SELECT COUNT(*) FROM messages")).fetchone())[0]
        media = (await (await d.execute("SELECT COUNT(*) FROM media")).fetchone())[0]
    await message.answer(
        f"✅ Статус: <b>{status}</b>\n"
        f"📝 Сообщений: <b>{msgs}</b>\n"
        f"🎨 Медиа: <b>{media}</b>"
    )


@router.message(Command("testapi"))
async def cmd_testapi(message: Message):
    """Админ-команда: тестовый запрос к API."""
    if message.from_user.id != ADMIN_ID:
        return

    import os
    from openai import OpenAI

    api_key = os.getenv("MIMO_API_KEY")
    base_url = os.getenv("MIMO_BASE_URL")
    model = os.getenv("MIMO_MODEL")

    await message.answer(
        f"🔍 <b>Тест API</b>\n"
        f"URL: <code>{base_url}</code>\n"
        f"MODEL: <code>{model}</code>\n"
        f"KEY: <code>{(api_key[:15] + '...') if api_key else 'НЕТ'}</code>"
    )

    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        r = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "привет"}],
            max_tokens=20,
        )
        await message.answer(f"✅ <b>ОТВЕТ:</b>\n{r.choices[0].message.content}")
    except Exception as e:
        await message.answer(f"❌ <b>ОШИБКА:</b>\n<code>{type(e).__name__}: {e}</code>")


@router.callback_query(F.data == "start_learning")
async def on_start_learning(callback: CallbackQuery):
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
async def handle_message(message: Message):
    """Единый обработчик: собирает при collecting, отвечает при ready."""
    if message.text and message.text.startswith("/"):
        return
    if message.chat.id == message.from_user.id:
        return

    status = await db.get_state("learning_status", "idle")

    # Режим сбора
    if status == "collecting":
        if message.text:
            username = message.from_user.username or message.from_user.first_name or "unknown"
            await db.save_message(message.from_user.id, username, message.text)
        if message.sticker:
            await db.save_media(message.sticker.file_id, "sticker")
        if message.animation:
            await db.save_media(message.animation.file_id, "animation")
        if message.photo:
            await db.save_media(message.photo[-1].file_id, "photo")
        return

    # Режим ответов
    if status == "ready" and message.text:
        # 5% шанс — кинуть случайное медиа
        if random.random() < 0.05:
            media = await db.get_random_media()
            if media:
                file_id, media_type = media
                try:
                    if media_type == "sticker":
                        await message.answer_sticker(file_id)
                    elif media_type == "animation":
                        await message.answer_animation(file_id)
                    elif media_type == "photo":
                        await message.answer_photo(file_id)
                    return
                except Exception as e:
                    print(f"Ошибка отправки медиа: {e}")

        # Основной ответ через MiMo
        try:
            reply = await generate_reply(message.text)
            if reply:
                await message.reply(reply)
        except Exception as e:
            print(f"Ошибка генерации: {e}")


async def check_learning_done(bot):
    """Планировщик — проверяет, не закончилось ли обучение."""
    status = await db.get_state("learning_status", "idle")
    if status != "collecting":
        return

    started_at = int(await db.get_state("learning_started_at", "0"))
    if time.time() - started_at < LEARNING_SECONDS:
        return

    await db.set_state("learning_status", "ready")

    if GROUP_ID:
        try:
            await bot.send_message(
                GROUP_ID,
                "✅ <b>Обучение закончено!</b>\n\nНапишите мне что-то."
            )
        except Exception as e:
            print(f"Не удалось отправить сообщение: {e}")
