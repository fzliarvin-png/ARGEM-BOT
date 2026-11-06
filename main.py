
import os
import uuid
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
CARD_NUMBER = os.getenv("CARD_NUMBER", "شماره کارت هنوز تنظیم نشده")
SUPPORT = "https://t.me/argemnet"

PLANS = {
    "10": ("10 گیگ", 60000),
    "20": ("20 گیگ", 80000),
    "30": ("30 گیگ", 100000),
    "50": ("50 گیگ", 150000),
    "100": ("100 گیگ", 220000),
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("10 گیگ - 60 هزار تومان", callback_data="plan:10")],
        [InlineKeyboardButton("20 گیگ - 80 هزار تومان", callback_data="plan:20")],
        [InlineKeyboardButton("30 گیگ - 100 هزار تومان", callback_data="plan:30")],
        [InlineKeyboardButton("50 گیگ - 150 هزار تومان", callback_data="plan:50")],
        [InlineKeyboardButton("100 گیگ - 220 هزار تومان", callback_data="plan:100")],
    ]
    await update.message.reply_text(
        "💎 به ARGEM خوش آمدید\n\n"
        "حجم موردنظرت رو انتخاب کن:\n"
        "تمام سرویس‌ها 30 روز اعتبار دارن.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"💬 پشتیبانی:\n{SUPPORT}")

async def choose_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    plan_id = query.data.split(":")[1]
    name, price = PLANS[plan_id]
    context.user_data["selected_plan"] = plan_id

    await query.message.reply_text(
        f"💎 بسته انتخابی: {name}\n"
        f"💰 مبلغ: {price:,} تومان\n"
        f"💳 شماره کارت:\n{CARD_NUMBER}\n\n"
        "پس از واریز، تصویر رسید پرداخت رو همین‌جا ارسال کن."
    )

async def receive_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    plan_id = context.user_data.get("selected_plan")

    if not plan_id:
        await update.message.reply_text("اول از منوی اصلی یک بسته انتخاب کن. /start")
        return

    if ADMIN_ID == 0:
        await update.message.reply_text("ربات هنوز تنظیمات مدیر را ندارد.")
        return

    name, price = PLANS[plan_id]
    order_id = uuid.uuid4().hex[:8]
    user = update.effective_user

    context.bot_data.setdefault("orders", {})
    context.bot_data["orders"][order_id] = {
        "user_id": user.id,
        "plan": name,
        "price": price,
        "status": "pending",
    }

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("تأیید پرداخت", callback_data=f"approve:{order_id}"),
            InlineKeyboardButton("رد پرداخت", callback_data=f"reject:{order_id}"),
        ]
    ])

    caption = (
        f"📥 سفارش جدید ARGEM\n\n"
        f"کد سفارش: {order_id}\n"
        f"کاربر: {user.full_name}\n"
        f"شناسه کاربر: {user.id}\n"
        f"بسته: {name}\n"
        f"مبلغ: {price:,} تومان\n\n"
        "لطفاً واریز را در حساب بانکی بررسی کن."
    )

    photo = update.message.photo[-1]
    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=photo.file_id,
        caption=caption,
        reply_markup=keyboard,
    )

    await update.message.reply_text(
        "✅ رسیدت برای مدیر ارسال شد.\n"
        "بعد از بررسی پرداخت، نتیجه بهت اطلاع داده می‌شه."
    )
    context.user_data.pop("selected_plan", None)

async def admin_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.message.reply_text("⛔ این بخش مخصوص مدیر است.")
        return

    action, order_id = query.data.split(":")
    order = context.bot_data.get("orders", {}).get(order_id)

    if not order or order["status"] != "pending":
        await query.message.reply_text("این سفارش پیدا نشد یا قبلاً بررسی شده.")
        return

    if action == "approve":
        order["status"] = "approved"
        context.user_data["awaiting_config"] = order_id
        await query.message.reply_text(
            f"پرداخت سفارش {order_id} تأیید شد.\n"
            "حالا کانفیگ مخصوص این مشتری رو در یک پیام متنی بفرست."
        )
    elif action == "reject":
        order["status"] = "rejected"
        await context.bot.send_message(
            chat_id=order["user_id"],
            text=f"پرداخت سفارش {order_id} تأیید نشد. لطفاً با پشتیبانی تماس بگیر: {SUPPORT}",
        )
        await query.message.reply_text("سفارش رد شد و به مشتری اطلاع داده شد.")

async def admin_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    order_id = context.user_data.get("awaiting_config")
    if not order_id:
        return

    order = context.bot_data.get("orders", {}).get(order_id)
    if not order:
        await update.message.reply_text("سفارش پیدا نشد.")
        context.user_data.pop("awaiting_config", None)
        return

    config = update.message.text
    await context.bot.send_message(
        chat_id=order["user_id"],
        text=(
            f"💎 سفارش {order_id} آماده شد!\n"
            f"بسته: {order['plan']}\n"
            "اعتبار: 30 روز\n\n"
            f"کانفیگ شما:\n{config}"
        ),
    )
    order["status"] = "completed"
    context.user_data.pop("awaiting_config", None)
    await update.message.reply_text("✅ کانفیگ برای مشتری ارسال شد.")

def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN تنظیم نشده است.")

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("support", support))
    app.add_handler(CallbackQueryHandler(choose_plan, pattern=r"^plan:"))
    app.add_handler(CallbackQueryHandler(admin_buttons, pattern=r"^(approve|reject):"))
    app.add_handler(MessageHandler(filters.PHOTO, receive_receipt))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_config))
    app.run_polling()

if __name__ == "__main__":
    main()
