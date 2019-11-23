import os
import logging
import trxbetbot.utils as utl
import trxbetbot.emoji as emo
import trxbetbot.constants as con

from telegram import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackQueryHandler
from trxbetbot.plugin import TrxBetBotPlugin
from MyQR import myqr


# TODO: Add logging and admin notification on error
class Deposit(TrxBetBotPlugin):

    QRCODES_DIR = "qr_codes"
    TRON_LOGO = "tron.png"

    def __enter__(self):
        self.add_handler(CallbackQueryHandler(self._callback))
        return self

    @TrxBetBotPlugin.threaded
    @TrxBetBotPlugin.send_typing
    def execute(self, bot, update, args):
        user_id = update.effective_user.id

        sql = self.get_global_resource("select_address.sql")
        res = self.execute_global_sql(sql, user_id)

        if not res["success"]:
            # TODO: show error
            return

        address = res["data"][0][1]
        privkey = res["data"][0][2]

        # Create directory for qr-code images
        qr_dir = os.path.join(self.get_plg_path(), self.QRCODES_DIR)
        os.makedirs(qr_dir, exist_ok=True)

        # Get file and path of qr-code image
        qr_name = f"{user_id}.png"
        qr_code = os.path.join(qr_dir, qr_name)

        if not os.path.isfile(qr_code):
            logo = os.path.join(self.get_plg_path(), con.DIR_RES, self.TRON_LOGO)

            myqr.run(
                address,
                version=1,
                level='H',
                picture=logo,
                colorized=True,
                contrast=1.0,
                brightness=1.0,
                save_name=qr_name,
                save_dir=qr_dir)

        with open(qr_code, "rb") as qr_pic:
            if update.effective_chat.type == "private":
                update.message.reply_photo(
                    photo=qr_pic,
                    caption=f"`{address}`",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=self._privkey_button(privkey))
            else:
                update.message.reply_photo(
                    photo=qr_pic,
                    caption=f"`{address}`",
                    parse_mode=ParseMode.MARKDOWN)

    def _privkey_button(self, privkey):
        menu = utl.build_menu([InlineKeyboardButton("Show Private Key", callback_data=privkey)])
        return InlineKeyboardMarkup(menu, resize_keyboard=True)

    def _callback(self, bot, update):
        query = update.callback_query
        message = query.message

        message.edit_caption(
            caption=f"*Address*\n`{message.caption}`\n\n*Private Key*\n`{query.data}`",
            parse_mode=ParseMode.MARKDOWN)

        msg = f"{emo.ALERT} DELETE AFTER VIEWING {emo.ALERT}"
        bot.answer_callback_query(query.id, msg)
