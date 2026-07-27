"""Telegram front end for OBD-Insight.

Paste a FORScan log (or send it as a .txt file) and get an instant,
color-coded, plain-English triage. Reuses the same parser/severity
engine as the terminal prototype in src/.
"""

import logging
import sys
from pathlib import Path

from telegram import LabeledPrice, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
)

BOT_DIR = Path(__file__).resolve().parent
REPO_ROOT = BOT_DIR.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(BOT_DIR))

from parser import parse_scan_session  # noqa: E402
from severity import classify_severity  # noqa: E402
from dtc_reference import explain  # noqa: E402
from storage import is_premium, record_scan, set_premium  # noqa: E402
import config  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SEVERITY_EMOJI = {"Critical": "\U0001F534", "Warning": "\U0001F7E1", "Informational": "⚪"}
STATUS_LABEL = {"new": "NEW", "repeated": "REPEATED", "returning": "RETURNING"}

PREMIUM_PAYLOAD = "obd-insight-premium-30d"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "OBD-Insight Bot\n\n"
        "Paste your FORScan log text (or send it as a .txt file) and I'll triage every "
        "fault code by severity in seconds.\n\n"
        "Free: severity + plain-English explanation for this scan.\n"
        "Premium: cross-scan history - see which codes are new, repeated, or returning "
        "after being cleared, so you know if an issue is getting worse or was never "
        "really fixed.\n\n"
        "Commands:\n"
        "/scan - paste or upload a log (or just send it, no command needed)\n"
        "/dtc <code> - look up a single code\n"
        "/upgrade - go premium\n"
        "/affiliate - promote this bot and earn Telegram Stars"
    )


async def dtc_lookup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Usage: /dtc P0300")
        return

    code = context.args[0].upper()
    severity = classify_severity(module=None, code=code)
    await update.message.reply_text(f"{SEVERITY_EMOJI[severity]} {severity}\n{code}: {explain(code)}")


async def handle_scan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text
    document = update.message.document

    if document:
        if not document.file_name.lower().endswith(".txt"):
            await update.message.reply_text("Please send a .txt FORScan log export.")
            return
        telegram_file = await document.get_file()
        raw = await telegram_file.download_as_bytearray()
        text = raw.decode("utf-8", errors="ignore")

    if not text or len(text) < 10:
        await update.message.reply_text("Paste your FORScan log text or send it as a .txt file.")
        return

    session = parse_scan_session(text)
    if not session["dtcs"]:
        await update.message.reply_text("No DTCs found in that log.")
        return

    user_id = update.effective_user.id
    vehicle_key = session["vehicle"].get("vin") or session["vehicle"].get("vehicle") or "default"
    premium = is_premium(config.DB_PATH, user_id)

    results = [
        {**dtc, "severity": classify_severity(dtc["module"], dtc["code"], raw_line=dtc["raw_line"])}
        for dtc in session["dtcs"]
    ]
    tracked = record_scan(config.DB_PATH, user_id, vehicle_key, results)

    lines = [f"Vehicle: {session['vehicle'].get('vehicle', 'Unknown vehicle')}", ""]
    for dtc in tracked:
        emoji = SEVERITY_EMOJI[dtc["severity"]]
        line = f"{emoji} {dtc['severity']:<13} | {dtc['module']} | {dtc['code']} - {explain(dtc['code'])}"
        if premium:
            line += f" [{STATUS_LABEL[dtc['status']]}]"
        lines.append(line)

    if not premium:
        lines.append("")
        lines.append(
            "Upgrade with /upgrade to see which codes are new, repeated, "
            "or returning after being cleared."
        )

    await update.message.reply_text("\n".join(lines))


async def upgrade(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    price = LabeledPrice("OBD-Insight Premium (30 days)", config.PREMIUM_STARS_PRICE)
    await context.bot.send_invoice(
        chat_id=update.effective_chat.id,
        title="OBD-Insight Premium",
        description=(
            "Unlock cross-scan history: see which fault codes are new, repeated, "
            "or returning after being cleared."
        ),
        payload=PREMIUM_PAYLOAD,
        provider_token="",  # Telegram Stars payments require an empty provider token
        currency="XTR",
        prices=[price],
    )


async def precheckout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.pre_checkout_query
    if query.invoice_payload != PREMIUM_PAYLOAD:
        await query.answer(ok=False, error_message="Something went wrong, please try /upgrade again.")
        return
    await query.answer(ok=True)


async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    set_premium(config.DB_PATH, update.effective_user.id, days=30)
    await update.message.reply_text("Premium activated for 30 days. Send another scan to see full history tracking.")


async def affiliate_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Run a car forum, FORScan group, or automotive channel?\n\n"
        "This bot's Affiliate Program is on in BotFather. To promote it: open Telegram, "
        "go to Settings > My Stars > Earn inside Telegram, find this bot, and tap Join. "
        "You'll get a unique referral link - anyone who starts the bot through it and "
        "buys Premium earns you a Star commission automatically, no extra setup needed."
    )


def build_application() -> Application:
    if not config.BOT_TOKEN:
        raise SystemExit("Set the BOT_TOKEN environment variable before starting the bot.")

    application = Application.builder().token(config.BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", start))
    application.add_handler(CommandHandler("dtc", dtc_lookup))
    application.add_handler(CommandHandler("scan", handle_scan))
    application.add_handler(CommandHandler("upgrade", upgrade))
    application.add_handler(CommandHandler("affiliate", affiliate_info))
    application.add_handler(MessageHandler(filters.Document.TXT, handle_scan))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_scan))
    application.add_handler(PreCheckoutQueryHandler(precheckout))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    return application


def main():
    application = build_application()
    application.run_polling()


if __name__ == "__main__":
    main()
