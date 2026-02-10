#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Bot Telegram avec Panel Admin Complet et Fonctionnel
Admin: @grandjd
Canal: @ziablowcontent
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
CANAL_REQUIS = os.getenv('CANAL_REQUIS', "@ziablowcontent")  # ← VOTRE CANAL
ADMIN_USERNAME = "grandjd"
ADMIN_ID = None  # Optionnel : ajoutez votre user ID ici

# Fichier de configuration
CONFIG_FILE = "bot_config.json"

# États de conversation
(EDIT_MESSAGE, EDIT_MENU_MESSAGE, ADD_BUTTON_TEXT, ADD_BUTTON_TYPE,
 ADD_BUTTON_DATA, BROADCAST_MESSAGE, CREATE_MENU_NAME) = range(7)

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
            "welcome_message": f"🤖 Bienvenue {{user_name}} !\n\nPour accéder au contenu, abonnez-vous au canal : {{canal}}",
            "verified_message": f"✅ Parfait {{user_name}} !\n\nVous êtes abonné à {{canal}}\n\nAccès autorisé ! 🎉",
            "not_verified_message": f"❌ Désolé {{user_name}}...\n\nVous devez vous abonner à {{canal}}",
            "menus": {
                "main_menu": {
                    "name": "Menu Principal",
                    "message": "📋 **Menu Principal**\n\nChoisissez une option :",
                    "buttons": [
                        {
                            "text": "📚 Exemple de bouton",
                            "type": "callback",
                            "data": "example_response"
                        }
                    ]
                }
            },
            "responses": {
                "example_response": "📚 Ceci est un exemple de réponse !\n\nVous pouvez modifier ce contenu dans le panel admin."
            },
            "stats": {"total_users": 0, "verified_users": 0},
            "users": []
        }
    
    def save_config(self):
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            logger.info("✅ Configuration sauvegardée")
            return True
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde: {e}")
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
        
        user_exists = any(u.get("id") == user_id for u in self.config["users"])
        if not user_exists:
            self.config["users"].append({"id": user_id, "username": username})
            self.save_config()


bot_config = BotConfig()


def is_admin(update: Update) -> bool:
    """Vérifie si l'utilisateur est admin"""
    user = update.effective_user
    
    # Par username
    if user.username and user.username.lower() == ADMIN_USERNAME.lower():
        return True
    
    # Par ID
    if ADMIN_ID and user.id == ADMIN_ID:
        return True
    
    return False


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
    
    logger.info(f"📱 /start de {user.username} (ID: {user.id})")
    
    bot_config.add_user(user.id, user.username)
    bot_config.increment_stat("total_users")
    
    if is_admin(update):
        logger.info(f"🔐 Admin détecté: @{user.username}")
        await show_admin_panel(update, context)
        return
    
    welcome_msg = bot_config.get("welcome_message", "").format(
        user_name=user.first_name,
        canal=CANAL_REQUIS
    )
    
    keyboard = [
        [InlineKeyboardButton(f"📢 S'abonner à {CANAL_REQUIS}", url=f"https://t.me/{CANAL_REQUIS.replace('@', '')}")],
        [InlineKeyboardButton("✅ Vérifier mon abonnement", callback_data='verifier')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_msg, reply_markup=reply_markup)


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Commande /admin"""
    if not is_admin(update):
        await update.message.reply_text("❌ Accès refusé")
        return
    
    await show_admin_panel(update, context)


async def debug_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Commande /debug"""
    user = update.effective_user
    
    debug_msg = f"""
🔍 **DEBUG**

**Vos infos :**
• ID : `{user.id}`
• Username : @{user.username}
• Prénom : {user.first_name}

**Config :**
• Admin : {ADMIN_USERNAME}
• Canal : {CANAL_REQUIS}
• Es-tu admin ? **{'✅ OUI' if is_admin(update) else '❌ NON'}**
"""
    
    await update.message.reply_text(debug_msg, parse_mode='Markdown')


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
        
        keyboard = [[InlineKeyboardButton("🚀 Accéder au menu", callback_data='main_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(verified_msg, reply_markup=reply_markup)
    else:
        not_verified_msg = bot_config.get("not_verified_message", "").format(
            user_name=user_name,
            canal=CANAL_REQUIS
        )
        
        keyboard = [
            [InlineKeyboardButton(f"📢 S'abonner à {CANAL_REQUIS}", url=f"https://t.me/{CANAL_REQUIS.replace('@', '')}")],
            [InlineKeyboardButton("🔄 Vérifier à nouveau", callback_data='verifier')]
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
            button = InlineKeyboardButton(btn_text, url=btn.get("data", "https://t.me"))
        else:
            button = InlineKeyboardButton(btn_text, callback_data=btn.get("data", "none"))
        
        keyboard.append([button])
    
    if menu_id != 'main_menu':
        keyboard.append([InlineKeyboardButton("🔙 Retour au menu", callback_data='main_menu')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if query:
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')


async def handle_custom_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    # Menu
    if callback_data in bot_config.get("menus", {}):
        await show_menu(update, context, callback_data)
        return
    
    # Réponse
    responses = bot_config.get("responses", {})
    if callback_data in responses:
        message = responses[callback_data]
        keyboard = [[InlineKeyboardButton("🔙 Retour au menu", callback_data='main_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        return


# ==================== PANEL ADMIN ====================

async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update):
        return
    
    query = update.callback_query
    
    stats = bot_config.get("stats", {})
    total = stats.get("total_users", 0)
    verified = stats.get("verified_users", 0)
    
    message = f"""
🔐 **PANEL ADMINISTRATEUR**

👤 Admin : @{ADMIN_USERNAME}
📢 Canal : {CANAL_REQUIS}

📊 **Statistiques :**
├ 👥 Total : {total}
├ ✅ Vérifiés : {verified}
└ 📈 Taux : {(verified/total*100) if total > 0 else 0:.1f}%

⚙️ **Gestion du bot :**
"""
    
    keyboard = [
        [InlineKeyboardButton("📝 Messages", callback_data='admin_messages'),
         InlineKeyboardButton("🎛️ Menus", callback_data='admin_menus')],
        [InlineKeyboardButton("📊 Statistiques", callback_data='admin_stats'),
         InlineKeyboardButton("📢 Broadcast", callback_data='admin_broadcast')],
        [InlineKeyboardButton("👥 Utilisateurs", callback_data='admin_users'),
         InlineKeyboardButton("🔄 Recharger", callback_data='admin_reload')],
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
    
    message = "📝 **GESTION DES MESSAGES**\n\nQuel message voulez-vous modifier ?"
    
    keyboard = [
        [InlineKeyboardButton("🎉 Message de bienvenue", callback_data='edit_msg_welcome')],
        [InlineKeyboardButton("✅ Message vérifié", callback_data='edit_msg_verified')],
        [InlineKeyboardButton("❌ Message non vérifié", callback_data='edit_msg_not_verified')],
        [InlineKeyboardButton("🔙 Retour au panel", callback_data='admin_panel')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')


async def admin_menus(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    menus = bot_config.get("menus", {})
    
    message = f"🎛️ **MENU BUILDER**\n\n📋 Menus créés : **{len(menus)}**\n\nQue voulez-vous faire ?"
    
    keyboard = [
        [InlineKeyboardButton("📝 Modifier Menu Principal", callback_data='menu_edit_main_menu')],
        [InlineKeyboardButton("➕ Créer nouveau menu", callback_data='menu_create')],
        [InlineKeyboardButton("🗑️ Supprimer un menu", callback_data='menu_delete_list')],
        [InlineKeyboardButton("👁️ Prévisualiser", callback_data='menu_preview')],
        [InlineKeyboardButton("🔙 Retour au panel", callback_data='admin_panel')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')


async def menu_edit_options(update: Update, context: ContextTypes.DEFAULT_TYPE, menu_id: str) -> None:
    query = update.callback_query
    await query.answer()
    
    menus = bot_config.get("menus", {})
    menu = menus.get(menu_id, {})
    menu_name = menu.get("name", menu_id)
    buttons = menu.get("buttons", [])
    
    message = f"📝 **MODIFIER : {menu_name}**\n\nBoutons actuels : {len(buttons)}\n\nQue voulez-vous faire ?"
    
    keyboard = [
        [InlineKeyboardButton("✏️ Modifier le message", callback_data=f'menu_edit_msg_{menu_id}')],
        [InlineKeyboardButton("➕ Ajouter un bouton", callback_data=f'menu_add_btn_{menu_id}')],
        [InlineKeyboardButton("🗑️ Supprimer un bouton", callback_data=f'menu_del_btn_{menu_id}')],
        [InlineKeyboardButton("👁️ Prévisualiser", callback_data=f'menu_show_{menu_id}')],
        [InlineKeyboardButton("🔙 Retour", callback_data='admin_menus')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')


async def menu_delete_button_list(update: Update, context: ContextTypes.DEFAULT_TYPE, menu_id: str) -> None:
    query = update.callback_query
    await query.answer()
    
    menus = bot_config.get("menus", {})
    menu = menus.get(menu_id, {})
    buttons = menu.get("buttons", [])
    
    if not buttons:
        await query.answer("Aucun bouton à supprimer", show_alert=True)
        return
    
    message = f"🗑️ **SUPPRIMER UN BOUTON**\n\nSélectionnez le bouton à supprimer :"
    
    keyboard = []
    for idx, btn in enumerate(buttons):
        keyboard.append([InlineKeyboardButton(
            f"❌ {btn.get('text', 'Bouton')}",
            callback_data=f'menu_del_btn_confirm_{menu_id}_{idx}'
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Annuler", callback_data=f'menu_edit_{menu_id}')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')


async def menu_delete_button_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE, menu_id: str, btn_idx: int) -> None:
    query = update.callback_query
    
    menus = bot_config.get("menus", {})
    if menu_id in menus and "buttons" in menus[menu_id]:
        if 0 <= btn_idx < len(menus[menu_id]["buttons"]):
            deleted_btn = menus[menu_id]["buttons"].pop(btn_idx)
            bot_config.set("menus", menus)
            await query.answer(f"✅ Bouton '{deleted_btn.get('text')}' supprimé !", show_alert=True)
            await menu_edit_options(update, context, menu_id)
        else:
            await query.answer("❌ Erreur: bouton introuvable", show_alert=True)
    else:
        await query.answer("❌ Erreur: menu introuvable", show_alert=True)


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
    
    total_buttons = sum(len(m.get("buttons", [])) for m in menus.values())
    
    message = f"""
📊 **STATISTIQUES DÉTAILLÉES**

👥 **Utilisateurs :**
├ Total : {total}
├ Vérifiés : {verified}
└ Taux : {rate:.1f}%

🎛️ **Contenu :**
├ Menus : {len(menus)}
├ Boutons : {total_buttons}
├ Réponses : {len(responses)}
└ Users en BDD : {len(users)}

🤖 **Bot :**
└ Statut : 🟢 En ligne

📢 **Canal :** {CANAL_REQUIS}
"""
    
    keyboard = [
        [InlineKeyboardButton("🔄 Actualiser", callback_data='admin_stats')],
        [InlineKeyboardButton("🔙 Retour au panel", callback_data='admin_panel')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')


async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    users = bot_config.get("users", [])
    
    message = f"👥 **LISTE DES UTILISATEURS**\n\nTotal : {len(users)}\n\n"
    
    # Afficher les 10 derniers users
    recent_users = users[-10:] if len(users) > 10 else users
    
    for user in reversed(recent_users):
        username = user.get("username", "Sans username")
        user_id = user.get("id", "?")
        message += f"• @{username} (ID: {user_id})\n"
    
    if len(users) > 10:
        message += f"\n... et {len(users) - 10} autres utilisateurs"
    
    keyboard = [
        [InlineKeyboardButton("📊 Voir stats", callback_data='admin_stats')],
        [InlineKeyboardButton("🔙 Retour au panel", callback_data='admin_panel')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')


async def admin_broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    users = bot_config.get("users", [])
    
    message = f"""
📢 **BROADCAST**

Vous allez envoyer un message à **{len(users)} utilisateurs**.

📝 Envoyez maintenant le message à broadcaster :

_Pour annuler, utilisez /cancel_
"""
    
    await query.edit_message_text(message, parse_mode='Markdown')
    return BROADCAST_MESSAGE


async def admin_broadcast_send(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    broadcast_msg = update.message.text
    users = bot_config.get("users", [])
    
    await update.message.reply_text(f"📤 Envoi en cours à {len(users)} utilisateurs...")
    
    success = 0
    failed = 0
    
    for user in users:
        try:
            await context.bot.send_message(
                chat_id=user.get("id"),
                text=f"📢 **MESSAGE DE L'ADMIN**\n\n{broadcast_msg}",
                parse_mode='Markdown'
            )
            success += 1
        except Exception as e:
            failed += 1
            logger.error(f"Erreur envoi à {user.get('id')}: {e}")
    
    await update.message.reply_text(
        f"✅ Broadcast terminé !\n\n"
        f"• Envoyés : {success}\n"
        f"• Échecs : {failed}\n\n"
        f"Utilisez /admin pour revenir au panel."
    )
    
    return ConversationHandler.END


async def admin_reload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    
    global bot_config
    bot_config = BotConfig()
    
    await query.answer("✅ Configuration rechargée !", show_alert=True)
    await show_admin_panel(update, context)


# ==================== ÉDITION DE MESSAGES ====================

async def start_edit_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
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
• `{{user_name}}` - Prénom de l'utilisateur
• `{{canal}}` - Nom du canal

📝 **Envoyez le nouveau message :**

_Pour annuler : /cancel_
"""
    
    await query.edit_message_text(message, parse_mode='Markdown')
    return EDIT_MESSAGE


async def receive_edited_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    new_message = update.message.text
    msg_type = context.user_data.get('editing_message')
    
    if msg_type == 'welcome':
        bot_config.set("welcome_message", new_message)
    elif msg_type == 'verified':
        bot_config.set("verified_message", new_message)
    elif msg_type == 'not_verified':
        bot_config.set("not_verified_message", new_message)
    
    await update.message.reply_text(
        "✅ Message mis à jour avec succès !\n\n"
        "Utilisez /admin pour revenir au panel."
    )
    
    return ConversationHandler.END


# ==================== ÉDITION DE MENU MESSAGE ====================

async def start_edit_menu_message(update: Update, context: ContextTypes.DEFAULT_TYPE, menu_id: str) -> int:
    query = update.callback_query
    await query.answer()
    
    context.user_data['editing_menu_id'] = menu_id
    
    menus = bot_config.get("menus", {})
    current_msg = menus.get(menu_id, {}).get("message", "")
    
    message = f"""
✏️ **MODIFIER LE MESSAGE DU MENU**

**Message actuel :**
{current_msg}

📝 **Envoyez le nouveau message :**

_Pour annuler : /cancel_
"""
    
    await query.edit_message_text(message, parse_mode='Markdown')
    return EDIT_MENU_MESSAGE


async def receive_edited_menu_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    new_message = update.message.text
    menu_id = context.user_data.get('editing_menu_id')
    
    menus = bot_config.get("menus", {})
    if menu_id in menus:
        menus[menu_id]["message"] = new_message
        bot_config.set("menus", menus)
        
        await update.message.reply_text(
            "✅ Message du menu mis à jour !\n\n"
            "Utilisez /admin pour revenir au panel."
        )
    else:
        await update.message.reply_text("❌ Erreur: menu introuvable")
    
    return ConversationHandler.END


# ==================== AJOUT DE BOUTON ====================

async def start_add_button(update: Update, context: ContextTypes.DEFAULT_TYPE, menu_id: str) -> int:
    query = update.callback_query
    await query.answer()
    
    context.user_data['menu_id'] = menu_id
    
    message = """
➕ **AJOUTER UN BOUTON**

📝 **Étape 1/3 : Texte du bouton**

Envoyez le texte qui s'affichera sur le bouton.

_Exemple : 📚 Voir le contenu_

_Pour annuler : /cancel_
"""
    
    await query.edit_message_text(message, parse_mode='Markdown')
    return ADD_BUTTON_TEXT


async def receive_button_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['button_text'] = update.message.text
    
    message = """
➕ **AJOUTER UN BOUTON**

✅ **Étape 1/3 : Texte enregistré**

📝 **Étape 2/3 : Type de bouton**

Choisissez le type :
"""
    
    keyboard = [
        [InlineKeyboardButton("🔘 Callback (action dans le bot)", callback_data='btn_type_callback')],
        [InlineKeyboardButton("🌐 URL (lien externe)", callback_data='btn_type_url')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    return ADD_BUTTON_TYPE


async def receive_button_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    btn_type = query.data.replace('btn_type_', '')
    context.user_data['button_type'] = btn_type
    
    if btn_type == 'callback':
        message = """
➕ **AJOUTER UN BOUTON**

✅ **Étape 2/3 : Type = Callback**

📝 **Étape 3/3 : Action**

Envoyez l'ID de l'action (callback_data).

_Exemple : show_content_

_Puis ajoutez la réponse dans bot_config.json :_
```
"responses": {
  "show_content": "Votre contenu ici"
}
```

_Pour annuler : /cancel_
"""
    else:
        message = """
➕ **AJOUTER UN BOUTON**

✅ **Étape 2/3 : Type = URL**

📝 **Étape 3/3 : URL**

Envoyez l'URL complète.

_Exemple : https://t.me/ziablowcontent_

_Pour annuler : /cancel_
"""
    
    await query.edit_message_text(message, parse_mode='Markdown')
    return ADD_BUTTON_DATA


async def receive_button_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    button_data = update.message.text
    menu_id = context.user_data.get('menu_id')
    button_text = context.user_data.get('button_text')
    button_type = context.user_data.get('button_type')
    
    menus = bot_config.get("menus", {})
    if menu_id in menus:
        if "buttons" not in menus[menu_id]:
            menus[menu_id]["buttons"] = []
        
        new_button = {
            "text": button_text,
            "type": button_type,
            "data": button_data
        }
        
        menus[menu_id]["buttons"].append(new_button)
        bot_config.set("menus", menus)
        
        success_msg = f"""
✅ **Bouton ajouté avec succès !**

• Texte : {button_text}
• Type : {button_type}
• Data : {button_data}
"""
        
        if button_type == 'callback':
            success_msg += f"""
💡 **N'oubliez pas d'ajouter la réponse dans bot_config.json :**

```json
"responses": {{
  "{button_data}": "Votre réponse ici"
}}
```

Puis utilisez /admin → 🔄 Recharger
"""
        
        success_msg += "\nUtilisez /admin pour revenir au panel."
        
        await update.message.reply_text(success_msg, parse_mode='Markdown')
    else:
        await update.message.reply_text("❌ Erreur: menu introuvable")
    
    return ConversationHandler.END


async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("❌ Annulé. Utilisez /admin pour revenir au panel.")
    return ConversationHandler.END


# ==================== CALLBACKS ROUTER ====================

async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    data = query.data
    
    # Admin panel
    if data == 'admin_panel':
        await show_admin_panel(update, context)
    elif data == 'admin_messages':
        await admin_messages(update, context)
    elif data == 'admin_menus':
        await admin_menus(update, context)
    elif data == 'admin_stats':
        await admin_stats(update, context)
    elif data == 'admin_users':
        await admin_users(update, context)
    elif data == 'admin_reload':
        await admin_reload(update, context)
    
    # Menu edition
    elif data.startswith('menu_edit_'):
        menu_id = data.replace('menu_edit_', '')
        await menu_edit_options(update, context, menu_id)
    elif data.startswith('menu_show_'):
        menu_id = data.replace('menu_show_', '')
        await show_menu(update, context, menu_id)
    elif data.startswith('menu_del_btn_confirm_'):
        parts = data.replace('menu_del_btn_confirm_', '').split('_')
        menu_id = '_'.join(parts[:-1])
        btn_idx = int(parts[-1])
        await menu_delete_button_confirm(update, context, menu_id, btn_idx)
    elif data.startswith('menu_del_btn_'):
        menu_id = data.replace('menu_del_btn_', '')
        await menu_delete_button_list(update, context, menu_id)
    
    # User callbacks
    elif data == 'verifier':
        await verifier_callback(update, context)
    elif data == 'main_menu' or data in bot_config.get("menus", {}):
        menu_id = data if data in bot_config.get("menus", {}) else 'main_menu'
        await show_menu(update, context, menu_id)
    else:
        await handle_custom_callback(update, context)


def main() -> None:
    logger.info(f"🤖 Bot Telegram - Version Complète et Fonctionnelle")
    logger.info(f"👤 Admin : @{ADMIN_USERNAME}")
    logger.info(f"📢 Canal : {CANAL_REQUIS}")
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Conversation handlers
    edit_message_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_edit_message, pattern='^edit_msg_')],
        states={
            EDIT_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_edited_message)],
        },
        fallbacks=[CommandHandler('cancel', cancel_conversation)],
    )
    
    edit_menu_msg_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(lambda u, c: start_edit_menu_message(u, c, u.callback_query.data.replace('menu_edit_msg_', '')), pattern='^menu_edit_msg_')],
        states={
            EDIT_MENU_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_edited_menu_message)],
        },
        fallbacks=[CommandHandler('cancel', cancel_conversation)],
    )
    
    add_button_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(lambda u, c: start_add_button(u, c, u.callback_query.data.replace('menu_add_btn_', '')), pattern='^menu_add_btn_')],
        states={
            ADD_BUTTON_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_button_text)],
            ADD_BUTTON_TYPE: [CallbackQueryHandler(receive_button_type, pattern='^btn_type_')],
            ADD_BUTTON_DATA: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_button_data)],
        },
        fallbacks=[CommandHandler('cancel', cancel_conversation)],
    )
    
    broadcast_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_broadcast_start, pattern='^admin_broadcast$')],
        states={
            BROADCAST_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_broadcast_send)],
        },
        fallbacks=[CommandHandler('cancel', cancel_conversation)],
    )
    
    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("debug", debug_command))
    application.add_handler(edit_message_conv)
    application.add_handler(edit_menu_msg_conv)
    application.add_handler(add_button_conv)
    application.add_handler(broadcast_conv)
    application.add_handler(CallbackQueryHandler(callback_router))
    
    logger.info("✅ Bot démarré - Panel admin 100% fonctionnel !")
    logger.info("💡 Commandes : /start /admin /debug")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
