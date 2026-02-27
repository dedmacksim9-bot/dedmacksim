import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from datetime import datetime, timedelta

# ================= НАСТРОЙКИ =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 7524452966
CHANNEL_ID = -1003583383646
# =============================================

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)

pending_posts = {}
reply_mode = {}
muted_users = {}


# ---------- ВСПОМОГАТЕЛЬНЫЕ ----------

def author_name(user: types.User) -> str:
    return f"@{user.username}" if user.username else user.full_name


def is_muted(user_id: int) -> bool:
    if user_id in muted_users:
        if datetime.now() < muted_users[user_id]:
            return True
        del muted_users[user_id]
    return False


def keyboard(post_id: int):
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("✅ Опубликовать", callback_data=f"pub_{post_id}"),
        InlineKeyboardButton("❌ Отклонить", callback_data=f"del_{post_id}")
    )
    kb.add(
        InlineKeyboardButton("✉️ Написать автору", callback_data=f"reply_{post_id}"),
        InlineKeyboardButton("🔇 Мут 1ч", callback_data=f"mute_{post_id}"),
        InlineKeyboardButton("🔊 Размут", callback_data=f"unmute_{post_id}")
    )
    return kb


# ---------- КОМАНДЫ ----------

@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    await msg.answer("👋 Привет! Отправь контент для предложки.")


@dp.message_handler(commands=["rule", "rules"])
async def rules(msg: types.Message):
    await msg.answer(
        "<b>📜 Правила:</b>\n\n"
        "1. Без спама\n"
        "2. Без оскорблений\n"
        "3. Без запрещённого контента\n\n"
        "Нарушения → мут."
    )


# ---------- ОСНОВНОЙ ХЭНДЛЕР (БЕЗ КОМАНД) ----------

@dp.message_handler(lambda message: not message.text or not message.text.startswith("/"),
                    content_types=types.ContentTypes.ANY)
async def handle(msg: types.Message):

    # ===== Ответ автору (ПОЛНАЯ поддержка медиа) =====
    if msg.from_user.id == ADMIN_ID and msg.from_user.id in reply_mode:
        user_id = reply_mode.pop(msg.from_user.id)
        prefix = "✉️ Сообщение от модерации:\n\n"

        if msg.text:
            await bot.send_message(user_id, prefix + msg.text)

        elif msg.photo:
            await bot.send_photo(
                user_id,
                msg.photo[-1].file_id,
                caption=prefix + (msg.caption or "")
            )

        elif msg.video:
            await bot.send_video(
                user_id,
                msg.video.file_id,
                caption=prefix + (msg.caption or "")
            )

        elif msg.animation:
            await bot.send_animation(
                user_id,
                msg.animation.file_id,
                caption=prefix + (msg.caption or "")
            )

        elif msg.document:
            await bot.send_document(
                user_id,
                msg.document.file_id,
                caption=prefix + (msg.caption or "")
            )

        elif msg.sticker:
            await bot.send_sticker(user_id, msg.sticker.file_id)

        await msg.answer("✅ Сообщение отправлено")
        return

    # ===== МУТ =====
    if is_muted(msg.from_user.id):
        await msg.answer("⛔ Вы временно не можете отправлять предложку.")
        return

    post_id = msg.message_id
    pending_posts[post_id] = msg
    author = author_name(msg.from_user)
    text_part = msg.text or msg.caption or ""

    header = f"<b>Новая предложка</b>\n<b>Автор:</b> {author}\n\n{text_part}"

    # ===== ОТПРАВКА АДМИНУ =====

    if msg.text:
        await bot.send_message(ADMIN_ID, header, reply_markup=keyboard(post_id))

    elif msg.photo:
        await bot.send_photo(
            ADMIN_ID,
            msg.photo[-1].file_id,
            caption=header,
            reply_markup=keyboard(post_id)
        )

    elif msg.video:
        await bot.send_video(
            ADMIN_ID,
            msg.video.file_id,
            caption=header,
            reply_markup=keyboard(post_id)
        )

    elif msg.animation:
        await bot.send_animation(
            ADMIN_ID,
            msg.animation.file_id,
            caption=header,
            reply_markup=keyboard(post_id)
        )

    elif msg.document:
        await bot.send_document(
            ADMIN_ID,
            msg.document.file_id,
            caption=header,
            reply_markup=keyboard(post_id)
        )

    elif msg.sticker:
        await bot.send_sticker(ADMIN_ID, msg.sticker.file_id)
        await bot.send_message(
            ADMIN_ID,
            f"<b>Новая предложка</b>\n<b>Автор:</b> {author}",
            reply_markup=keyboard(post_id)
        )

    await msg.answer("📨 Отправлено на модерацию.")


# ---------- CALLBACK ----------

@dp.callback_query_handler(lambda c: c.data.startswith("reply_"))
async def reply(call: types.CallbackQuery):
    post_id = int(call.data.split("_")[1])
    msg = pending_posts.get(post_id)

    if not msg:
        await call.answer("Пост не найден")
        return

    reply_mode[call.from_user.id] = msg.from_user.id
    await call.message.reply("✍️ Напиши сообщение автору:")
    await call.answer()


@dp.callback_query_handler(lambda c: c.data.startswith("mute_"))
async def mute(call: types.CallbackQuery):
    post_id = int(call.data.split("_")[1])
    msg = pending_posts.get(post_id)

    muted_users[msg.from_user.id] = datetime.now() + timedelta(hours=1)
    await call.message.reply("🔇 Пользователь замучен на 1 час")
    await call.answer()


@dp.callback_query_handler(lambda c: c.data.startswith("unmute_"))
async def unmute(call: types.CallbackQuery):
    post_id = int(call.data.split("_")[1])
    msg = pending_posts.get(post_id)

    muted_users.pop(msg.from_user.id, None)
    await call.message.reply("🔊 Пользователь размучен")
    await call.answer()


@dp.callback_query_handler(lambda c: c.data.startswith("del_"))
async def delete(call: types.CallbackQuery):
    pending_posts.pop(int(call.data.split("_")[1]), None)

    if call.message.text:
        await call.message.edit_text("❌ Отклонено")
    else:
        await call.message.edit_caption("❌ Отклонено")

    await call.answer()


@dp.callback_query_handler(lambda c: c.data.startswith("pub_"))
async def publish(call: types.CallbackQuery):
    post_id = int(call.data.split("_")[1])
    msg = pending_posts.get(post_id)

    if not msg:
        await call.answer("Пост не найден")
        return

    author = author_name(msg.from_user)
    text_part = msg.text or msg.caption or ""
    signature = f"\n\n<b>Прислал:</b> {author}"

    if msg.text:
        await bot.send_message(CHANNEL_ID, text_part + signature)

    elif msg.photo:
        await bot.send_photo(
            CHANNEL_ID,
            msg.photo[-1].file_id,
            caption=text_part + signature
        )

    elif msg.video:
        await bot.send_video(
            CHANNEL_ID,
            msg.video.file_id,
            caption=text_part + signature
        )

    elif msg.animation:
        await bot.send_animation(
            CHANNEL_ID,
            msg.animation.file_id,
            caption=text_part + signature
        )

    elif msg.document:
        await bot.send_document(
            CHANNEL_ID,
            msg.document.file_id,
            caption=text_part + signature
        )

    elif msg.sticker:
        await bot.send_sticker(CHANNEL_ID, msg.sticker.file_id)
        await bot.send_message(CHANNEL_ID, f"<b>Прислал:</b> {author}")

    pending_posts.pop(post_id, None)

    if call.message.text:
        await call.message.edit_text("✅ Опубликовано")
    else:
        await call.message.edit_caption("✅ Опубликовано")

    await call.answer()


# ---------- ЗАПУСК ----------

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)