import os
import json
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from flask import Flask
from threading import Thread

# Configurar Flask para el health check
health_app = Flask(__name__)

@health_app.route('/')
def home():
    return "Bot activo", 200

def run_health_app():
    health_app.run(port=5000, host='0.0.0.0')

# Cargar respuestas desde JSON o crear nuevo si no existe
def load_responses():
    try:
        # Intenta cargar desde archivo
        with open('responses.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Si no existe, crea uno básico
        default_responses = {
            "default": "🤖 No entiendo ese mensaje",
            "hola": "¡Hola! ¿En qué puedo ayudarte?",
            "adios": "¡Hasta pronto!",
            "gracias": "De nada, ¡estoy para servirte!"
        }
        # Guarda el archivo por primera vez
        with open('responses.json', 'w') as f:
            json.dump(default_responses, f, indent=2)
        return default_responses

# Guardar respuestas en JSON
def save_responses(responses):
    with open('responses.json', 'w') as f:
        json.dump(responses, f, indent=2)

# Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_markdown_v2(
        fr'Hola {user.mention_markdown_v2()}\! Soy un bot de respuestas automáticas\.'
        '\n\nUsa /edit para configurar respuestas'
    )

# Comando /edit - Interfaz de edición
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

# Manejar nueva respuesta
async def new_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['editing'] = 'new'
    await update.message.reply_text(
        "Envía el formato:\n"
        "`palabra clave: respuesta`\n\n"
        "Ejemplo:\n"
        "saludo: ¡Hola! ¿Cómo estás?",
        parse_mode="Markdown"
    )

# Editar respuesta existente
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

# Procesar mensajes de texto
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

# Manejar errores
async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Error: {context.error}")

def main():
    # Obtener token de Telegram
    TOKEN = os.getenv('TELEGRAM_TOKEN')
    if not TOKEN:
        print("ERROR: No se encontró TELEGRAM_TOKEN en las variables de entorno")
        return
    
    # Configurar aplicación
    application = Application.builder().token(TOKEN).build()
    
    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("edit", edit_responses))
    application.add_handler(CommandHandler("nueva", new_response))
    application.add_handler(CommandHandler("editar", edit_response))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    application.add_error_handler(error)
    
    return application

if __name__ == '__main__':
    # Iniciar el servidor de health check en un hilo separado
    health_thread = Thread(target=run_health_app, daemon=True)
    health_thread.start()
    
    # Iniciar el bot
    bot_app = main()
    
    # Para Render: Obtener puerto de variable de entorno
    port = int(os.environ.get('PORT', 5000))
    print(f"Usando puerto: {port}")
    
    # Usar polling para recibir actualizaciones
    bot_app.run_polling()
    print("Bot en ejecución...")