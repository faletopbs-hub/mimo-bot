from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import Command
import time
import random
import aiosqlite
from pathlib import Path

from config import ADMIN_ID, LEARNING_DAYS, GROUP_ID
import database as db
from ai import generate_reply

router = Router()

LEARNING_SECONDS = LEARNING_DAYS * 24 * 60 * 60


def is_admin(message: Message) -> bool:
    return message.from_user.id == ADMIN_ID


@router.message(Command("start"))
async def cmd_start(message: Message):
    if message.chat.id == message.from_user.id:
        await message.answer(
            "Привет! Я Федя. Управление — только в личке.\n"
            "Команды: /setprompt, /getprompt, /users, /adduser, /deluser, /dump, /setready"
        )
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎓 Начать обучение", callback_data="start_learning")]
    ])
    await message.answer(
        "Готов к обучению. Нажми кнопку ниже.",
        reply_markup=keyboard
    )


@router.message(Command("setready"))
async def cmd_setready(message: Message):
    if not is_admin(message):
        return
    await db.set_state("learning_status", "ready")
    status = await db.get_state("learning_status")
    async with aiosqlite.connect(db.DB_PATH) as d:
        msgs = (await (await d.execute("SELECT COUNT(*) FROM messages")).fetchone())[0]
        media = (await (await d.execute("SELECT COUNT(*) FROM media")).fetchone())[0]
    await message.answer(f"✅ Статус: <b>{status}</b>\n📝 Сообщений: <b>{msgs}</b>\n🎨 Медиа: <b>{media}</b>")


@router.message(Command("setprompt"))
async def cmd_setprompt(message: Message):
    if not is_admin(message):
        return
    text = message.text.replace("/setprompt", "", 1).strip()
    if not text:
        await message.answer("Использование: /setprompt <текст>")
        return
    await db.set_prompt(text)
    await message.answer(f"✅ Промпт сохранён:\n\n<code>{text}</code>")


@router.message(Command("getprompt"))
async def cmd_getprompt(message: Message):
    if not is_admin(message):
        return
    prompt = await db.get_prompt()
    if not prompt:
        await message.answer("Промпт пуст. Задай через /setprompt <текст>")
    else:
        await message.answer(f"Текущий промпт:\n\n<code>{prompt}</code>")


@router.message(Command("users"))
async def cmd_users(message: Message):
    if not is_admin(message):
        return
    users = await db.list_users()
    lines = [f"<code>{uid}</code> — {name} ({gender})" for uid, name, gender in users]
    await message.answer("👥 Известные люди:\n" + "\n".join(lines))


@router.message(Command("adduser"))
async def cmd_adduser(message: Message):
    if not is_admin(message):
        return
    parts = message.text.split(maxsplit=3)
    if len(parts) < 4:
        await message.answer("Использование: /adduser <id> <имя> <род>")
        return
    try:
        uid = int(parts[1])
    except ValueError:
        await message.answer("ID должен быть числом.")
        return
    name = parts[2]
    gender = parts[3]
    await db.add_user(uid, name, gender)
    await message.answer(f"✅ Добавлен: {uid} — {name} ({gender})")


@router.message(Command("deluser"))
async def cmd_deluser(message: Message):
    if not is_admin(message):
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Использование: /deluser <id>")
        return
    try:
        uid = int(parts[1])
    except ValueError:
        await message.answer("ID должен быть числом.")
        return
    await db.del_user(uid)
    await message.answer(f"✅ Удалён: {uid}")


@router.message(Command("dump"))
async def cmd_dump(message: Message):
    if not is_admin(message):
        return
    async with aiosqlite.connect(db.DB_PATH) as d:
        async with d.execute("SELECT user_id, username, text, date FROM messages ORDER BY id") as cur:
            msgs = await cur.fetchall()
        async with d.execute("SELECT file_id, media_type, date FROM media ORDER BY id") as cur:
            media = await cur.fetchall()

    dump_path = Path("/app/data/dump.txt")
    with open(dump_path, "w", encoding="utf-8") as f:
        f.write("=== СООБЩЕНИЯ ===\n")
        for uid, uname, text, date in msgs:
            f.write(f"[{date}] {uid} ({uname}): {text}\n")
        f.write("\n=== МЕДИА ===\n")
        for fid, mtype, date in media:
            f.write(f"[{date}] {mtype}: {fid}\n")

    await message.answer_document(FSInputFile(dump_path), caption=f"📦 Сообщений: {len(msgs)}, медиа: {len(media)}")


@router.callback_query(F.data == "start_learning")
async def on_start_learning(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Нет прав.", show_alert=True)
        return
    status = await db.get_state("learning_status", "idle")
    if status == "collecting":
        await callback.answer("⚠️ Уже идёт.", show_alert=True)
        return
    if status == "ready":
        await callback.answer("✅ Уже завершено.", show_alert=True)
        return
    await db.set_state("learning_status", "collecting")
    await db.set_state("learning_started_at", str(int(time.time())))
    await callback.message.edit_text(
        f"🎓 <b>Обучение началось!</b>\nСбор сообщений {LEARNING_DAYS} дней."
    )
    await callback.answer("Запущено")


@router.message(F.text | F.sticker | F.animation | F.photo)
async def handle_message(message: Message):
    if message.text and message.text.startswith("/"):
        return
    if message.chat.id == message.from_user.id:
        return

    status = await db.get_state("learning_status", "idle")

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

    if status == "ready" and message.text:
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
                    print(f"Ошибка медиа: {e}")

        try:
            reply = await generate_reply(message.from_user.id, message.text)
            if reply:
                await message.reply(reply)
        except Exception as e:
            print(f"Ошибка генерации: {e}")


async def check_learning_done(bot):
    status = await db.get_state("learning_status", "idle")
    if status != "collecting":
        return
    started_at = int(await db.get_state("learning_started_at", "0"))
    if time.time() - started_at < LEARNING_SECONDS:
        return
    await db.set_state("learning_status", "ready")
    if GROUP_ID:
        try:
            await bot.send_message(GROUP_ID, "✅ <b>Обучение закончено!</b>\n\nНапишите мне что-то.")
        except Exception as e:
            print(f"Не удалось отправить: {e}")
