#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Bot Telegram avec Panel Admin Complet et Menu Builder
Admin: @grandjd
Inspiré de MenuBuilder Bot
"""

import logging
import json
import os
from typing import Dict, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN', "7553192698:AAGU4yYCTjYJ5iVYVtbMREKIDbLbZZ6cb7s")
CANAL_REQUIS = os.getenv('CANAL_REQUIS', "@ziablowcontent")
ADMIN_USERNAME = "grandjd"

# Fichier de configuration
CONFIG_FILE = "bot_config.json"

# États de conversation
(EDIT_MESSAGE, ADD_BUTTON_TEXT, ADD_BUTTON_ACTION, ADD_BUTTON_URL,
 CREATE_MENU_NAME, CREATE_MENU_MESSAGE, BROADCAST_MESSAGE) = range(7)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class BotConfig:
    """Gestion de la configuration du bot"""
    
    def __init__(self, config_file: str = CONFIG_FILE):
        self.config_file = config_file
        self.config = self.load_config()
    
    def load_config(self) -> dict:
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        
        return {
            "welcome_message": "🤖 Bienvenue {user_name} !\n\nPour accéder au contenu, abonnez-vous au canal : {canal}",
            "verified_message": "✅ Parfait {user_name} !\n\nVous êtes abonné au canal {canal}\n\nAccès autorisé ! 🎉",
            "not_verified_message": "❌ Désolé {user_name}...\n\nVous devez vous abonner à {canal}",
            "menus": {
                "main_menu": {
                    "name": "Menu Principal",
                    "message": "📋 Menu Principal\n\nChoisissez une option :",
                    "buttons": []
                }
            },
            "responses": {},
            "stats": {"total_users": 0, "verified_users": 0},
            "users": []
        }
    
    def save_config(self):
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Erreur sauvegarde: {e}")
            return False
    
    def get(self, key: str, default=None):
        return self.config.get(key, default)
    
    def set(self, key: str, value):
        self.config[key] = value
        self.save_config()
    
    def increment_stat(self, stat_name: str):
        if "stats" not in self.config:
            self.config["stats"] = {}
        self.config["stats"][stat_name] = self.config["stats"].get(stat_name, 0) + 1
        self.save_config()
    
    def add_user(self, user_id: int, username: str = None):
        if "users" not in self.config:
            self.config["users"] = []
        if user_id not in self.config["users"]:
            self.config["users"].append({"id": user_id, "username": username})
            self.save_config()


bot_config = BotConfig()


def is_admin(update: Update) -> bool:
    user = update.effective_user
    return user.username == ADMIN_USERNAME


async def verifier_abonnement(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=CANAL_REQUIS, user_id=user_id)
        return member.status in ['creator', 'administrator', 'member']
    except Exception as e:
        logger.error(f"Erreur vérification: {e}")
        return False


# ==================== COMMANDES ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    
    # Ajouter l'utilisateur
    bot_config.add_user(user.id, user.username)
    bot_config.increment_stat("total_users")
    
    # Si admin
    if is_admin(update):
        await show_admin_panel(update, context)
        return
    
    # Message de bienvenue
    welcome_msg = bot_config.get("welcome_message", "").format(
        user_name=user.first_name,
        canal=CANAL_REQUIS
    )
    
    keyboard = [
        [InlineKeyboardButton("📢 S'abonner", url=f"https://t.me/{CANAL_REQUIS.replace('@', '')}")],
        [InlineKeyboardButton("✅ Vérifier", callback_data='verifier')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_msg, reply_markup=reply_markup)


async def verifier_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_name = query.from_user.first_name
    
    if await verifier_abonnement(user_id, context):
        bot_config.increment_stat("verified_users")
        
        verified_msg = bot_config.get("verified_message", "").format(
            user_name=user_name,
            canal=CANAL_REQUIS
        )
        
        keyboard = [[InlineKeyboardButton("🚀 Menu", callback_data='main_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(verified_msg, reply_markup=reply_markup)
    else:
        not_verified_msg = bot_config.get("not_verified_message", "").format(
            user_name=user_name,
            canal=CANAL_REQUIS
        )
        
        keyboard = [
            [InlineKeyboardButton("📢 S'abonner", url=f"https://t.me/{CANAL_REQUIS.replace('@', '')}")],
            [InlineKeyboardButton("🔄 Réessayer", callback_data='verifier')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(not_verified_msg, reply_markup=reply_markup)


async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, menu_id: str) -> None:
    query = update.callback_query
    if query:
        await query.answer()
    
    menus = bot_config.get("menus", {})
    
    if menu_id not in menus:
        if query:
            await query.edit_message_text("❌ Menu introuvable")
        return
    
    menu = menus[menu_id]
    message = menu.get("message", "Menu")
    buttons_data = menu.get("buttons", [])
    
    keyboard = []
    for btn in buttons_data:
        btn_text = btn.get("text", "Bouton")
        btn_type = btn.get("type", "callback")
        
        if btn_type == "url":
            button = InlineKeyboardButton(btn_text, url=btn.get("url", "https://t.me"))
        else:
            button = InlineKeyboardButton(btn_text, callback_data=btn.get("data", "none"))
        
        keyboard.append([button])
    
    if menu_id != 'main_menu':
        keyboard.append([InlineKeyboardButton("🔙 Retour", callback_data='main_menu')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if query:
        await query.edit_message_text(message, reply_markup=reply_markup)
    else:
        await update.message.reply_text(message, reply_markup=reply_markup)


async def handle_custom_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    # Menu
    if callback_data in bot_config.get("menus", {}):
        await show_menu(update, context, callback_data)
        return
    
    # Réponse personnalisée
    responses = bot_config.get("responses", {})
    if callback_data in responses:
        message = responses[callback_data]
        keyboard = [[InlineKeyboardButton("🔙 Menu", callback_data='main_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup)
        return


# ==================== PANEL ADMIN ====================

async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update):
        return
    
    query = update.callback_query
    
    stats = bot_config.get("stats", {})
    total_users = stats.get("total_users", 0)
    verified_users = stats.get("verified_users", 0)
    
    message = f"""
🔐 **PANEL ADMIN**

👤 Admin : @{ADMIN_USERNAME}
📢 Canal : {CANAL_REQUIS}

📊 **Stats :**
👥 Total : {total_users}
✅ Vérifiés : {verified_users}

⚙️ **Gestion :**
"""
    
    keyboard = [
        [InlineKeyboardButton("📝 Messages", callback_data='admin_messages'),
         InlineKeyboardButton("🎛️ Menus", callback_data='admin_menus')],
        [InlineKeyboardButton("📊 Stats", callback_data='admin_stats'),
         InlineKeyboardButton("📢 Broadcast", callback_data='admin_broadcast')],
        [InlineKeyboardButton("⚙️ Config", callback_data='admin_config'),
         InlineKeyboardButton("🔄 Reload", callback_data='admin_reload')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if query:
        await query.answer()
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')


async def admin_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    message = "📝 **MESSAGES**\n\nQuel message modifier ?"
    
    keyboard = [
        [InlineKeyboardButton("🎉 Bienvenue", callback_data='edit_msg_welcome')],
        [InlineKeyboardButton("✅ Vérifié", callback_data='edit_msg_verified')],
        [InlineKeyboardButton("❌ Non vérifié", callback_data='edit_msg_not_verified')],
        [InlineKeyboardButton("🔙 Retour", callback_data='admin_panel')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')


async def admin_menus(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    menus = bot_config.get("menus", {})
    
    message = f"🎛️ **MENU BUILDER**\n\n📋 Menus : {len(menus)}"
    
    keyboard = [
        [InlineKeyboardButton("➕ Nouveau", callback_data='menu_new')],
        [InlineKeyboardButton("📝 Modifier", callback_data='menu_list_edit')],
        [InlineKeyboardButton("🗑️ Supprimer", callback_data='menu_list_delete')],
        [InlineKeyboardButton("👁️ Preview", callback_data='menu_preview')],
        [InlineKeyboardButton("🔙 Retour", callback_data='admin_panel')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')


async def menu_list_for_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    menus = bot_config.get("menus", {})
    
    message = "📝 **MODIFIER UN MENU**\n\nSélectionnez :"
    
    keyboard = []
    for menu_id, menu_data in menus.items():
        menu_name = menu_data.get("name", menu_id)
        btn_count = len(menu_data.get("buttons", []))
        keyboard.append([InlineKeyboardButton(
            f"{menu_name} ({btn_count} btns)",
            callback_data=f'menu_edit_{menu_id}'
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Retour", callback_data='admin_menus')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')


async def menu_edit_options(update: Update, context: ContextTypes.DEFAULT_TYPE, menu_id: str) -> None:
    query = update.callback_query
    await query.answer()
    
    menus = bot_config.get("menus", {})
    menu = menus.get(menu_id, {})
    menu_name = menu.get("name", menu_id)
    
    message = f"📝 **MODIFIER : {menu_name}**\n\nQue faire ?"
    
    keyboard = [
        [InlineKeyboardButton("✏️ Message", callback_data=f'menu_msg_{menu_id}')],
        [InlineKeyboardButton("➕ Ajouter bouton", callback_data=f'menu_addbtn_{menu_id}')],
        [InlineKeyboardButton("🗑️ Suppr. bouton", callback_data=f'menu_delbtn_{menu_id}')],
        [InlineKeyboardButton("🔙 Retour", callback_data='menu_list_edit')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')


async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    stats = bot_config.get("stats", {})
    menus = bot_config.get("menus", {})
    responses = bot_config.get("responses", {})
    users = bot_config.get("users", [])
    
    total = stats.get("total_users", 0)
    verified = stats.get("verified_users", 0)
    rate = (verified / total * 100) if total > 0 else 0
    
    message = f"""
📊 **STATISTIQUES**

👥 **Utilisateurs :**
├ Total : {total}
├ Vérifiés : {verified}
└ Taux : {rate:.1f}%

🎛️ **Contenu :**
├ Menus : {len(menus)}
├ Réponses : {len(responses)}
└ Users DB : {len(users)}

🤖 Statut : 🟢 En ligne
"""
    
    keyboard = [
        [InlineKeyboardButton("🔄 Refresh", callback_data='admin_stats')],
        [InlineKeyboardButton("🔙 Retour", callback_data='admin_panel')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')


async def admin_reload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    
    global bot_config
    bot_config = BotConfig()
    
    await query.answer("✅ Config rechargée !", show_alert=True)
    await show_admin_panel(update, context)


# ==================== CONVERSATIONS POUR ÉDITION ====================

async def start_edit_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    # Extraire le type de message
    msg_type = query.data.replace('edit_msg_', '')
    context.user_data['editing_message'] = msg_type
    
    current_msg = ""
    if msg_type == 'welcome':
        current_msg = bot_config.get("welcome_message", "")
    elif msg_type == 'verified':
        current_msg = bot_config.get("verified_message", "")
    elif msg_type == 'not_verified':
        current_msg = bot_config.get("not_verified_message", "")
    
    message = f"""
✏️ **MODIFIER LE MESSAGE**

**Message actuel :**
{current_msg}

**Variables disponibles :**
• {{user_name}} - Prénom de l'utilisateur
• {{canal}} - Nom du canal

📝 Envoyez le nouveau message :
"""
    
    await query.edit_message_text(message, parse_mode='Markdown')
    return EDIT_MESSAGE


async def receive_edited_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    new_message = update.message.text
    msg_type = context.user_data.get('editing_message')
    
    # Sauvegarder
    if msg_type == 'welcome':
        bot_config.set("welcome_message", new_message)
    elif msg_type == 'verified':
        bot_config.set("verified_message", new_message)
    elif msg_type == 'not_verified':
        bot_config.set("not_verified_message", new_message)
    
    await update.message.reply_text("✅ Message mis à jour !\n\nUtilisez /start pour revenir au panel admin.")
    
    return ConversationHandler.END


async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("❌ Annulé. Utilisez /start")
    return ConversationHandler.END


# ==================== CALLBACKS ROUTER ====================

async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    data = query.data
    
    # Admin
    if data == 'admin_panel':
        await show_admin_panel(update, context)
    elif data == 'admin_messages':
        await admin_messages(update, context)
    elif data == 'admin_menus':
        await admin_menus(update, context)
    elif data == 'admin_stats':
        await admin_stats(update, context)
    elif data == 'admin_reload':
        await admin_reload(update, context)
    elif data == 'menu_list_edit':
        await menu_list_for_edit(update, context)
    elif data.startswith('menu_edit_'):
        menu_id = data.replace('menu_edit_', '')
        await menu_edit_options(update, context, menu_id)
    
    # User
    elif data == 'verifier':
        await verifier_callback(update, context)
    elif data == 'main_menu' or data in bot_config.get("menus", {}):
        menu_id = data if data in bot_config.get("menus", {}) else 'main_menu'
        await show_menu(update, context, menu_id)
    else:
        await handle_custom_callback(update, context)


def main() -> None:
    logger.info(f"🤖 Bot avec Panel Admin")
    logger.info(f"👤 Admin : @{ADMIN_USERNAME}")
    logger.info(f"📢 Canal : {CANAL_REQUIS}")
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Conversation handler pour édition de messages
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_edit_message, pattern='^edit_msg_')],
        states={
            EDIT_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_edited_message)],
        },
        fallbacks=[CommandHandler('cancel', cancel_conversation)],
    )
    
    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(callback_router))
    
    logger.info("✅ Bot démarré !")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
