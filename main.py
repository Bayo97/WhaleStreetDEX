import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

# Ustawienie logowania
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# TOKEN bota odczytywany ze zmiennej środowiskowej
# Ważne: Ta zmienna MUSI być ustawiona w Railway (TELEGRAM_TOKEN)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

# --- Funkcje Menu ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Obsługuje polecenie /start."""
    await update.message.reply_text("Witaj w Bot do Skanowania DEX! Użyj /dex, aby zobaczyć menu.")

async def dex_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Obsługuje polecenie /dex i wyświetla główne menu."""
    keyboard = [
        [
            InlineKeyboardButton("Solana Top Anomalie", callback_data='solana_anomalies'),
        ],
        [
            InlineKeyboardButton("BASE Nowe Pary", callback_data='base_new_pairs'),
        ],
        [
            InlineKeyboardButton("Zmień Ustawienia", callback_data='settings'),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Wybierz opcję skanowania DEX:",
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Obsługuje kliknięcia przycisków Inline."""
    query = update.callback_query
    
    # Usuwa stan 'ładowania' z przycisku
    await query.answer()

    data = query.data
    
    if data == 'solana_anomalies':
        response = "🚀 Skanowanie Solany pod kątem nietypowych przyspieszeń wolumenu..."
    elif data == 'base_new_pairs':
        response = "🆕 Szukanie nowych par o niskiej kapitalizacji na BASE..."
    elif data == 'settings':
        response = "⚙️ Ustawienia: Tutaj będą zarządzane progi (TODO)."
    else:
        response = "Nieznana akcja."
        
    # Edytuje oryginalną wiadomość
    await query.edit_message_text(text=f"Wybrano: {response}\n\nWróć do menu: /dex")


# --- Główna Funkcja Bota ---

def main() -> None:
    """Startuje bota."""
    if not TELEGRAM_TOKEN:
        logging.error("Błąd: Zmienna środowiskowa TELEGRAM_TOKEN nie jest ustawiona.")
        # W środowisku lokalnym możesz tu dodać token tymczasowo,
        # ale na Railway musi być w zmiennych środowiskowych!
        return

    # Tworzenie aplikacji i przekazanie tokena
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Handlery
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("dex", dex_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    logging.info("Bot jest uruchomiony, nasłuchiwanie na polecenia...")
    # Używamy poolingu, który jest prosty do wdrożenia na Railway
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
