from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def user_menu(owner_username: str) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text="💎 Beli VIP", callback_data="vip:buy"),
            InlineKeyboardButton(text="👀 Preview", callback_data="vip:preview"),
        ],
    ]
    if owner_username:
        rows.append([InlineKeyboardButton(text="💬 Chat Owner", url=f"https://t.me/{owner_username.lstrip('@')}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def vip_packages() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🟣 VIP Perminggu", callback_data="vip:package:weekly"),
            InlineKeyboardButton(text="🟡 VIP Permanent", callback_data="vip:package:permanent"),
        ],
        [InlineKeyboardButton(text="⬅️ Kembali", callback_data="menu:user")],
    ])


def payment_keyboard(invoice: str, pay_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Buka Pembayaran", url=pay_url)],
        [
            InlineKeyboardButton(text="🔴 Cancel", callback_data=f"pay:cancel:{invoice}"),
            InlineKeyboardButton(text="⬅️ Kembali", callback_data="vip:buy"),
        ],
    ])


def admin_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🟢 Tambahkan VIP", callback_data="admin:set_vip"),
            InlineKeyboardButton(text="🔵 Upload Konten", callback_data="admin:upload"),
        ],
        [
            InlineKeyboardButton(text="🟣 Atur Preview", callback_data="admin:preview"),
            InlineKeyboardButton(text="🟠 Broadcast", callback_data="admin:broadcast"),
        ],
        [InlineKeyboardButton(text="⚙️ Git Pull", callback_data="admin:gitpull")],
    ])


def upload_done_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Selesai Upload", callback_data="admin:upload_done")],
    ])
