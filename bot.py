import os
import json
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes
)
from telegram.ext import filters  # Cambio clave aquí

# Cargar variables de entorno
load_dotenv()
TOKEN = os.getenv('TELEGRAM_TOKEN')
RESPONSES_FILE = 'responses.json'

# Cargar respuestas desde JSON
def load_responses():
    try:
        with open(RESPONSES_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"default": "🤖 No entiendo ese mensaje"}

# Guardar respuestas en JSON
def save_responses(responses):
    with open(RESPONSES_FILE, 'w') as f:
        json.dump(responses, f, indent=2)

# Comando /start (ahora async)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_markdown_v2(
        fr'Hola {user.mention_markdown_v2()}\! Soy un bot de respuestas automáticas\.'
        '\n\nUsa /edit para configurar respuestas'
    )

# Comando /edit (ahora async)
async def edit_responses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    responses = load_responses()
    keyboard = []
    
    for key in responses.keys():
        if key != "default":
            keyboard.append([f"/editar {key}"])
    
    keyboard.append(["/nueva"])
    
    await update.message.reply_text(
        "✏️ **Editor de respuestas**\n"
        "Usa:\n"
        "- /nueva: Agregar nueva respuesta\n"
        "- /editar [palabra]: Modificar respuesta existente\n"
        "- /eliminar [palabra]: Borrar respuesta\n\n"
        "Respuestas existentes:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True),
        parse_mode="Markdown"
    )

# Manejar nueva respuesta (ahora async)
async def new_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['editing'] = 'new'
    await update.message.reply_text(
        "Envía el formato:\n"
        "`palabra clave: respuesta`\n\n"
        "Ejemplo:\n"
        "saludo: ¡Hola! ¿Cómo estás?",
        parse_mode="Markdown"
    )

# Editar respuesta existente (ahora async)
async def edit_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        keyword = context.args[0].lower()
        responses = load_responses()
        
        if keyword in responses:
            context.user_data['editing_key'] = keyword
            await update.message.reply_text(
                f"Actualiza la respuesta para '{keyword}':\n"
                f"Actual: `{responses[keyword]}`\n\n"
                "Envía el nuevo texto:",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(f"❌ '{keyword}' no existe")
    except IndexError:
        await update.message.reply_text("Debes especificar una palabra clave: /editar [palabra]")

# Procesar mensajes de texto (ahora async)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.lower()
    responses = load_responses()
    
    # Modo edición
    if 'editing' in context.user_data:
        if ':' in user_text:
            keyword, response = user_text.split(':', 1)
            keyword = keyword.strip().lower()
            
            responses[keyword] = response.strip()
            save_responses(responses)
            
            del context.user_data['editing']
            await update.message.reply_text(f"✅ Respuesta para '{keyword}' guardada!")
        else:
            await update.message.reply_text("Formato incorrecto. Usa:\n`palabra clave: respuesta`", parse_mode="Markdown")
        return
    
    # Modo actualización
    if 'editing_key' in context.user_data:
        keyword = context.user_data['editing_key']
        responses[keyword] = user_text
        save_responses(responses)
        
        del context.user_data['editing_key']
        await update.message.reply_text(f"✅ '{keyword}' actualizada!")
        return
    
    # Respuesta automática
    response = responses.get(user_text, responses['default'])
    await update.message.reply_text(response)

# Manejar errores (ahora async)
async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Error: {context.error}")

def main():
    # Configuración actualizada para v20.x
    application = Application.builder().token(TOKEN).build()
    
    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("edit", edit_responses))
    application.add_handler(CommandHandler("nueva", new_response))
    application.add_handler(CommandHandler("editar", edit_response))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    application.add_error_handler(error)

    application.run_polling()
    print("Bot en ejecución...")

if __name__ == '__main__':
    main()