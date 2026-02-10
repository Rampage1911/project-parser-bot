import os
from dotenv import load_dotenv
load_dotenv()

from telegram import LabeledPrice, Update
from telegram.ext import (
    Application, CommandHandler, ContextTypes, PreCheckoutQueryHandler
)

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Простая "память" (для теста). Для продакшена лучше SQLite.
paid_users = set()

STARS_PRICE = 150  # 10 Stars

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Команды:\n"
        "/unlock — оплатить доступ (150 ⭐)\n"
        "/parse — использовать парсер"
    )

async def unlock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Для Stars провайдер не нужен: provider_token = "".
    # Валюта должна быть XTR, цена в "минимальных единицах" = просто количество Stars.
    prices = [LabeledPrice(label="Доступ к парсеру", amount=STARS_PRICE)]

    await update.message.reply_invoice(
        title="Доступ к парсеру",
        description="Разблокировка функций бота на 30 дней (пример).",
        payload=f"unlock:{update.effective_user.id}",
        provider_token="",
        currency="XTR",
        prices=prices,
    )

async def precheckout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Telegram спрашивает бота: "Ок проводить платеж?"
    await update.pre_checkout_query.answer(ok=True)

async def successful_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    paid_users.add(user_id)
    await update.message.reply_text("✅ Оплата получена! Доступ открыт. Теперь можно /parse")

async def parse_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in paid_users:
        await update.message.reply_text("⛔ Нужно оплатить доступ: /unlock (150 ⭐)")
        return

    # Тут вставляешь свою логику "парсера"
    await update.message.reply_text("🧩 Парсер запущен (пример). Пришли данные/ссылку — и я обработаю.")

def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не найден в .env")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("unlock", unlock))
    app.add_handler(PreCheckoutQueryHandler(precheckout_handler))
    app.add_handler(CommandHandler("parse", parse_cmd))

    # В PTB успешная оплата приходит как message.successful_payment
    app.add_handler(CommandHandler("help", start))
    app.add_handler(
        # ловим любые сообщения с successful_payment
        # (в PTB это делается через MessageHandler, но проще так:
        # используем "application.add_handler" с "filters.SUCCESSFUL_PAYMENT" если нужно)
        # Оставим универсально через обработчик обновлений:
        # однако PTB удобнее через MessageHandler(filters.SUCCESSFUL_PAYMENT, ...)
        # чтобы не усложнять — добавь ниже по желанию.
        # ---
        # Ниже добавим правильный вариант:
        # ---
        None
    )

if __name__ == "__main__":
    # Добавим корректный handler для successful_payment перед запуском
    from telegram.ext import MessageHandler, filters

    def build_app():
        app = Application.builder().token(BOT_TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("unlock", unlock))
        app.add_handler(PreCheckoutQueryHandler(precheckout_handler))
        app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))
        app.add_handler(CommandHandler("parse", parse_cmd))
        return app


application = build_app()

port = int(os.environ.get("PORT", "10000"))
base_url = os.environ.get("RENDER_EXTERNAL_URL")

if not base_url:
    raise RuntimeError("RENDER_EXTERNAL_URL не найден (он появится на Render)")

webhook_path = f"/{os.environ.get('BOT_TOKEN')}"

application.run_webhook(
    listen="0.0.0.0",
    port=port,
    url_path=webhook_path.lstrip("/"),
    webhook_url=f"{base_url}{webhook_path}",
    drop_pending_updates=True,
)
