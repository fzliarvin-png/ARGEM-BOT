import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = int(os.environ["ADMIN_ID"])
CARD_NUMBER = os.environ["CARD_NUMBER"]

PLANS = {
    "10": ("10 گیگ", 60000),
    "20": ("20 گیگ", 80000),
    "30": ("30 گیگ", 100000),
    "50": ("50 گیگ", 150000),
    "100": ("100 گیگ", 220000),
}

SUPPORT = "https://t.me/argemnet"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(f"{name} - {price:,} تومان", callback_data=f"plan:{key}")]
        for key, (name, price) in PLANS.items()
    ]

    await update.message.reply_text(
        "💎 به ARGEM خوش آمدید\n\n"
        "حجم موردنظرت رو انتخاب کن:\n"
        "تمام سرویس‌ها ۳۰ روز اعتبار دارن.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


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
        "بعد از واریز، تصویر رسید رو همین‌جا ارسال کن."
    )


async def receive_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    plan_id = context.user_data.get("selected_plan")

    if not plan_id:
        await update.message.reply_text("اول یک بسته انتخاب کن: /start")
        return

    name, price = PLANS[plan_id]
    user = update.effective_user

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ تأیید پرداخت", callback_data=f"approve:{user.id}:{plan_id}"),
        InlineKeyboardButton("❌ رد پرداخت", callback_data=f"reject:{user.id}"),
    ]])

    caption = (
        f"📥 سفارش جدید ARGEM\n\n"
        f"کاربر: {user.full_name}\n"
        f"شناسه: {user.id}\n"
        f"بسته: {name}\n"
        f"مبلغ: {price:,} تومان\n\n"
        "قبل از تأیید، واریز را در حساب بانکی بررسی کن."
    )

    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=update.message.photo[-1].file_id,
        caption=caption,
        reply_markup=keyboard,
    )

    await update.message.reply_text("✅ رسید برای مدیر ارسال شد.")
    context.user_data.pop("selected_plan", None)


async def admin_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.message.reply_text("⛔ این بخش مخصوص مدیر است.")
        return

    parts = query.data.split(":")
    action = parts[0]
    user_id = int(parts[1])

    if action == "approve":
        plan_id = parts[2]
        context.user_data["awaiting_config"] = (user_id, plan_id)
        await query.message.reply_text(
            "پرداخت را بررسی کردی؟ اگر تأیید شده، حالا کانفیگ مشتری را در یک پیام متنی بفرست."
        )

    elif action == "reject":
        await context.bot.send_message(
            chat_id=user_id,
            text=f"پرداخت تأیید نشد. برای پیگیری: {SUPPORT}",
        )
        await query.message.reply_text("سفارش رد شد.")


async def admin_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    pending = context.user_data.get("awaiting_config")
    if not pending:
        return

    user_id, plan_id = pending
    name, price = PLANS[plan_id]

    await context.bot.send_message(
        chat_id=user_id,
        text=(
            f"💎 سفارش ARGEM آماده شد!\n"
            f"بسته: {name}\n"
            "اعتبار: ۳۰ روز\n\n"
            f"کانفیگ شما:\n{update.message.text}"
        ),
    )

    context.user_data.pop("awaiting_config", None)
    await update.message.reply_text("✅ کانفیگ برای مشتری ارسال شد.")


async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"💬 پشتیبانی:\n{SUPPORT}")


def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("support", support))
    app.add_handler(CallbackQueryHandler(choose_plan, pattern=r"^plan:"))
    app.add_handler(CallbackQueryHandler(admin_buttons, pattern=r"^(approve|reject):"))
    app.add_handler(MessageHandler(filters.PHOTO, receive_receipt))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_config))

    logging.info("ARGEM bot is starting...")
    app.run_polling()


if __name__ == "__main__":
    main()
