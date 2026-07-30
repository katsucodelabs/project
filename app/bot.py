from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ChatMemberStatus
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, Message

from config import get_settings
from app.db import Database
from app.keyboards import admin_menu, payment_keyboard, user_menu, vip_packages
from app.pakasir import PakasirClient

settings = get_settings()
bot = Bot(settings.bot_token)
db = Database(settings.mongo_uri, settings.mongo_db)
pakasir = PakasirClient(settings.pakasir_slug, settings.pakasir_api_key, settings.pakasir_base_url)
router = Router()


class AdminState(StatesGroup):
    waiting_vip_chat = State()
    waiting_upload = State()
    waiting_preview = State()
    waiting_broadcast = State()


def is_privileged(user_id: int) -> bool:
    return user_id in settings.privileged_ids


async def is_chat_admin(user_id: int, chat_id: int | None) -> bool:
    if not chat_id:
        return False
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR}
    except Exception:
        return False


async def can_manage(user_id: int) -> bool:
    return is_privileged(user_id) or await is_chat_admin(user_id, settings.vip_channel_id)


async def save_user(message: Message) -> None:
    user = message.from_user
    if user:
        await db.upsert_user(user.id, {"username": user.username, "full_name": user.full_name})


async def copy_without_forward(message: Message, chat_id: int) -> None:
    await bot.copy_message(chat_id=chat_id, from_chat_id=message.chat.id, message_id=message.message_id)


@router.message(Command("start"))
async def start(message: Message) -> None:
    await save_user(message)
    if message.from_user and await can_manage(message.from_user.id):
        await message.answer("Panel owner/admin:", reply_markup=admin_menu())
    else:
        await message.answer("Selamat datang. Silakan pilih menu:", reply_markup=user_menu(settings.owner_username))


@router.callback_query(F.data == "menu:user")
async def back_user(callback: CallbackQuery) -> None:
    await callback.message.edit_text("Silakan pilih menu:", reply_markup=user_menu(settings.owner_username))
    await callback.answer()


@router.callback_query(F.data == "vip:buy")
async def buy_vip(callback: CallbackQuery) -> None:
    await callback.message.edit_text("Pilih paket VIP:", reply_markup=vip_packages())
    await callback.answer()


@router.callback_query(F.data.startswith("vip:package:"))
async def choose_package(callback: CallbackQuery) -> None:
    package = callback.data.split(":")[-1]
    amount = settings.vip_price_monthly if package == "monthly" else settings.vip_price_permanent
    invoice = pakasir.create_invoice(amount)
    now = datetime.now(timezone.utc)
    await db.db.purchases.insert_one({
        "invoice": invoice.invoice, "user_id": callback.from_user.id, "package": package,
        "amount": amount, "status": "pending", "created_at": now,
        "expires_at": now + timedelta(minutes=settings.payment_timeout_minutes),
    })
    await callback.message.answer_photo(
        invoice.qris_url,
        caption=f"Invoice: `{invoice.invoice}`\nPaket: {package}\nTotal: Rp{amount:,}\nSilakan bayar sebelum timeout.",
        parse_mode="Markdown",
        reply_markup=payment_keyboard(invoice.invoice, invoice.payment_url),
    )
    asyncio.create_task(watch_payment(invoice.invoice))
    await callback.answer()


async def watch_payment(invoice: str) -> None:
    while True:
        purchase = await db.db.purchases.find_one({"invoice": invoice})
        if not purchase or purchase["status"] != "pending":
            return
        if datetime.now(timezone.utc) > purchase["expires_at"]:
            await db.db.purchases.update_one({"invoice": invoice}, {"$set": {"status": "expired"}})
            return
        if await pakasir.is_paid(invoice, purchase["amount"]):
            await activate_vip(purchase)
            return
        await asyncio.sleep(settings.payment_check_interval_seconds)


async def activate_vip(purchase: dict[str, Any]) -> None:
    until = None if purchase["package"] == "permanent" else datetime.now(timezone.utc) + timedelta(days=30)
    await db.db.users.update_one({"user_id": purchase["user_id"]}, {"$set": {"is_vip": True, "vip_until": until}}, upsert=True)
    await db.db.purchases.update_one({"invoice": purchase["invoice"]}, {"$set": {"status": "paid", "paid_at": datetime.now(timezone.utc)}})
    invite = None
    if settings.vip_channel_id:
        invite = await bot.create_chat_invite_link(settings.vip_channel_id, member_limit=1, expire_date=datetime.now(timezone.utc) + timedelta(hours=24))
    text = "Pembayaran berhasil!"
    if invite:
        text += f"\nLink VIP sekali pakai: {invite.invite_link}"
    await bot.send_message(purchase["user_id"], text)
    if settings.purchase_log_chat_id:
        await bot.send_message(settings.purchase_log_chat_id, f"✅ Pembelian VIP berhasil\nUser: {purchase['user_id']}\nInvoice: {purchase['invoice']}\nPaket: {purchase['package']}")


@router.callback_query(F.data.startswith("pay:cancel:"))
async def cancel_payment(callback: CallbackQuery) -> None:
    invoice = callback.data.split(":")[-1]
    await db.db.purchases.update_one({"invoice": invoice, "user_id": callback.from_user.id}, {"$set": {"status": "cancelled"}})
    await callback.message.edit_caption(caption="Pembayaran dibatalkan.")
    await callback.answer("Dibatalkan")


@router.callback_query(F.data == "vip:preview")
async def preview(callback: CallbackQuery) -> None:
    image = await db.get_setting("preview_image", settings.preview_image)
    if image:
        await callback.message.answer_photo(image, caption="Preview VIP", reply_markup=user_menu(settings.owner_username))
    else:
        await callback.message.answer("Preview belum diatur.", reply_markup=user_menu(settings.owner_username))
    await callback.answer()


@router.callback_query(F.data == "admin:set_vip")
async def set_vip(callback: CallbackQuery, state: FSMContext) -> None:
    if not await can_manage(callback.from_user.id):
        return await callback.answer("Tidak diizinkan", show_alert=True)
    await state.set_state(AdminState.waiting_vip_chat)
    await callback.message.answer("Kirim ID channel VIP, contoh: -1001234567890")
    await callback.answer()


@router.message(AdminState.waiting_vip_chat)
async def receive_vip_chat(message: Message, state: FSMContext) -> None:
    if not message.text or not message.text.lstrip("-").isdigit():
        return await message.answer("ID tidak valid.")
    await db.set_setting("vip_channel_id", int(message.text))
    settings.vip_channel_id = int(message.text)
    await state.clear()
    await message.answer("Channel VIP tersimpan.", reply_markup=admin_menu())


@router.callback_query(F.data == "admin:upload")
async def upload(callback: CallbackQuery, state: FSMContext) -> None:
    if not await can_manage(callback.from_user.id):
        return await callback.answer("Tidak diizinkan", show_alert=True)
    await state.set_state(AdminState.waiting_upload)
    await callback.message.answer("Kirim media/pesan apa pun. Bot akan menyalin ke channel VIP tanpa label forward.")
    await callback.answer()


@router.message(AdminState.waiting_upload)
async def receive_upload(message: Message, state: FSMContext) -> None:
    chat_id = await db.get_setting("vip_channel_id", settings.vip_channel_id)
    if not chat_id:
        return await message.answer("Channel VIP belum diatur.")
    await copy_without_forward(message, int(chat_id))
    await state.clear()
    await message.answer("Konten berhasil dikirim tanpa tanda diteruskan.", reply_markup=admin_menu())


@router.callback_query(F.data == "admin:preview")
async def set_preview(callback: CallbackQuery, state: FSMContext) -> None:
    if not await can_manage(callback.from_user.id):
        return await callback.answer("Tidak diizinkan", show_alert=True)
    await state.set_state(AdminState.waiting_preview)
    await callback.message.answer("Kirim gambar preview atau URL/file_id gambar.")
    await callback.answer()


@router.message(AdminState.waiting_preview)
async def receive_preview(message: Message, state: FSMContext) -> None:
    value = message.photo[-1].file_id if message.photo else (message.text or "")
    if not value:
        return await message.answer("Kirim gambar atau URL/file_id.")
    await db.set_setting("preview_image", value)
    await state.clear()
    await message.answer("Preview tersimpan.", reply_markup=admin_menu())


@router.callback_query(F.data == "admin:broadcast")
async def broadcast(callback: CallbackQuery, state: FSMContext) -> None:
    if not await can_manage(callback.from_user.id):
        return await callback.answer("Tidak diizinkan", show_alert=True)
    await state.set_state(AdminState.waiting_broadcast)
    await callback.message.answer("Kirim pesan/media yang akan dibroadcast ke semua user /start.")
    await callback.answer()


@router.message(AdminState.waiting_broadcast)
async def receive_broadcast(message: Message, state: FSMContext) -> None:
    sent = failed = 0
    for user_id in await db.all_user_ids():
        try:
            await copy_without_forward(message, user_id)
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1
    await state.clear()
    await message.answer(f"Broadcast selesai. Terkirim: {sent}, gagal: {failed}", reply_markup=admin_menu())


@router.message(F.forward_origin | F.forward_from | F.forward_from_chat)
async def strip_forward_to_target(message: Message) -> None:
    await save_user(message)
    if not message.from_user or not await can_manage(message.from_user.id):
        return await message.answer("Fitur hapus tanda diteruskan hanya untuk owner/admin.", reply_markup=user_menu(settings.owner_username))
    if not settings.target_chat_id:
        return await message.answer("TARGET_CHAT_ID belum diatur di .env.")
    await copy_without_forward(message, settings.target_chat_id)
    await message.answer("Pesan berhasil dikirim ke target tanpa tanda diteruskan.")


async def main() -> None:
    await db.init_indexes()
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
