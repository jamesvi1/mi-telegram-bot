import os
import json
import http.server
import socketserver
from threading import Thread
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from dotenv import load_dotenv

# Servidor HTTP simple para health checks
class HealthHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Bot activo')

def run_health_server(port=5000):
    with socketserver.TCPServer(("", port), HealthHandler) as httpd:
        print(f"Health check en puerto {port}")
        httpd.serve_forever()

# Cargar variables de entorno
load_dotenv()  # Carga el archivo .env en la misma carpeta
TOKEN = os.getenv('TELEGRAM_TOKEN')  # Usamos la variable aquí

# Cargar respuestas desde JSON o crear nuevo si no existe
def load_responses():
    try:
        # Intenta cargar desde archivo
        with open('responses.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Si no existe o hay error, crea uno básico
        default_responses = {
            "default": "🤖 No entiendo ese mensaje",
            "hola": "¡Hola! ¿En qué puedo ayudarte?",
            "adios": "¡Hasta pronto!",
            "gracias": "De nada, ¡estoy para servirte!"
        }
        # Guarda el archivo por primera vez
        save_responses(default_responses)
        return default_responses

# Guardar respuestas en JSON
def save_responses(responses):
    with open('responses.json', 'w', encoding='utf-8') as f:
        json.dump(responses, f, indent=2, ensure_ascii=False)

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

# Comando para eliminar respuesta
async def delete_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        keyword = context.args[0].lower()
        responses = load_responses()
        
        if keyword in responses and keyword != "default":
            del responses[keyword]
            save_responses(responses)
            await update.message.reply_text(f"✅ Respuesta para '{keyword}' eliminada!")
        else:
            await update.message.reply_text(f"❌ '{keyword}' no existe o no se puede eliminar")
    except IndexError:
        await update.message.reply_text("Debes especificar una palabra clave: /eliminar [palabra]")

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
            parts = user_text.split(':', 1)
            if len(parts) == 2:
                keyword, response = parts
                keyword = keyword.strip().lower()
                
                # Validar que la palabra clave no esté vacía
                if keyword:
                    responses[keyword] = response.strip()
                    save_responses(responses)
                    del context.user_data['editing']
                    await update.message.reply_text(f"✅ Respuesta para '{keyword}' guardada!")
                else:
                    await update.message.reply_text("La palabra clave no puede estar vacía")
            else:
                await update.message.reply_text("Formato incorrecto. Usa: `palabra clave: respuesta`", parse_mode="Markdown")
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
    global TOKEN
    
    if not TOKEN:
        print("ERROR: No se encontró TELEGRAM_TOKEN en las variables de entorno")
        print("Por favor, crea un archivo .env con TELEGRAM_TOKEN=tu_token")
        return None
    
    print(f"Token encontrado: {TOKEN[:5]}...")  # Muestra parte del token
    
    # Configurar aplicación
    application = Application.builder().token(TOKEN).build()
    
    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("edit", edit_responses))
    application.add_handler(CommandHandler("nueva", new_response))
    application.add_handler(CommandHandler("editar", edit_response))
    application.add_handler(CommandHandler("eliminar", delete_response))  # Nuevo handler para eliminar
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    application.add_error_handler(error)
    
    return application

if __name__ == '__main__':
    # Obtener puerto de Render o usar 5000 por defecto
    port = int(os.environ.get('PORT', 5000))
    print(f"Configurando health check en puerto {port}")
    
    # Iniciar servidor de health check en un hilo separado
    health_thread = Thread(target=run_health_server, args=(port,), daemon=True)
    health_thread.start()
    
    # Iniciar el bot
    bot_app = main()
    
    if bot_app:
        print("Iniciando bot...")
        try:
            bot_app.run_polling()
            print("Bot en ejecución...")
        except Exception as e:
            print(f"Error al iniciar el bot: {e}")
    else:
        print("No se pudo iniciar el bot debido a la falta del token.")
        # Esperar para que puedas ver el mensaje
        import time
        time.sleep(10)
