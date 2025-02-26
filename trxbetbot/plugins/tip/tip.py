import logging
import trxbetbot.emoji as emo
import trxbetbot.utils as utl
import trxbetbot.constants as con

from trxbetbot.trxapi import TRXAPI
from telegram import ParseMode, Chat
from datetime import datetime, timedelta
from trxbetbot.plugin import TrxBetBotPlugin


# TODO: Add possibility to immediately create a wallet if user doesn't have one (the receiver)
class Tip(TrxBetBotPlugin):

    def __enter__(self):
        if not self.global_table_exists("tips"):
            sql = self.get_resource("create_tips.sql")
            self.execute_global_sql(sql)
        return self

    @TrxBetBotPlugin.threaded
    @TrxBetBotPlugin.send_typing
    def execute(self, bot, update, args):
        reply = update.message.reply_to_message

        # Tip the user that you reply to
        if reply:
            if len(args) != 1:
                msg = f"{emo.ERROR} You are tipping the user you reply to. " \
                      "Only allowed argument is the amount."
                logging.error(f"{msg} - {update}")
                update.message.reply_text(msg)
                return

            amount = args[0]
            to_username = reply.from_user.username.replace("@", "")

        # Tip user specified in message
        else:
            if len(args) != 2:
                update.message.reply_text(
                    text=f"Usage:\n{self.get_usage()}",
                    parse_mode=ParseMode.MARKDOWN)
                return

            amount = args[0]
            to_username = args[1].replace("@", "")

        try:
            # Check if amount is valid
            float(amount)
        except:
            msg = f"{emo.ERROR} Provided amount is not valid"
            logging.error(f"{msg} - {update}")
            update.message.reply_text(msg)
            return

        sql = self.get_resource("select_user.sql")
        res = self.execute_global_sql(sql, to_username)

        if not res["success"]:
            msg = f"{emo.ERROR} Something went wrong. Please contact @HashLotto_Admin"
            logging.error(f"{msg} - {update}")
            update.message.reply_text(msg)
            return

        if not res["data"]:
            msg = f"{emo.ERROR} User @{to_username} doesn't have a wallet yet"
            logging.error(f"{msg} - {update}")
            update.message.reply_text(msg)
            return

        to_user_id = res["data"][0][0]
        to_address = res["data"][0][5]

        from_user_id = update.effective_user.id
        from_username = update.effective_user.username
        from_firstname = update.effective_user.first_name

        sql = self.get_global_resource("select_address.sql")
        res = self.execute_global_sql(sql, from_user_id)

        if not res["success"]:
            msg = f"{emo.ERROR} Something went wrong. Please contact @HashLotto_Admin"
            update.message.reply_text(msg)
            return

        data = res["data"]

        if not data:
            msg = f"{emo.ERROR} You don't have a wallet yet. " \
                  f"Create one by talking to the bot @{bot.name}"
            logging.error(f"{msg} - {update}")
            update.message.reply_text(msg)
            return

        trx_kwargs = dict()
        trx_kwargs["private_key"] = data[0][2]
        trx_kwargs["default_address"] = data[0][1]

        tron = TRXAPI(**trx_kwargs)

        balance = tron.re(tron.trx.get_balance)
        available_amount = tron.fromSun(balance)

        # Check if address has enough balance
        if float(amount) > float(available_amount):
            msg = f"{emo.ERROR} Not enough funds. Your balance is `{available_amount}` TRX"
            update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
            logging.error(f"{msg} - {data[0][1]} - {update}")
            return

        try:
            send = tron.re(tron.trx.send, to_address, float(amount))

            if "transaction" not in send:
                logging.error(send)
                raise Exception("key 'transaction' not in send result")

            txid = send["transaction"]["txID"]

            explorer_link = f"https://tronscan.org/#/transaction/{txid}"
            msg = f"{emo.DONE} @{utl.esc_md(from_username)} tipped @{utl.esc_md(to_username)} with " \
                  f"`{amount}` TRX. View [Block Explorer]({explorer_link}) (wait ~1 minute)"

            message = update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

            if bot.get_chat(update.message.chat_id).type == Chat.PRIVATE:
                remove_time = self.config.get("private_remove_after")
            else:
                remove_time = self.config.get("public_remove_after")

            if message:
                self.run_job(
                    self._remove_msg,
                    datetime.now() + timedelta(seconds=remove_time),
                    context=f"{message.chat_id}_{message.message_id}")

            backslash = "\n"
            logging.info(f"{msg.replace(backslash, '')} - {update}")

            try:
                if from_username:
                    # Tipping user has a username
                    bot.send_message(
                        to_user_id,
                        f"You received `{amount}` TRX from @{utl.esc_md(from_username)}",
                        parse_mode=ParseMode.MARKDOWN)
                else:
                    # Tipping user doesn't have a username
                    bot.send_message(
                        to_user_id,
                        f"You received `{amount}` TRX from @{utl.esc_md(from_firstname)}",
                        parse_mode=ParseMode.MARKDOWN)
            except:
                logging.info(f"User {to_username} ({to_user_id}) couldn't be notified about tip")

            sent_amount = tron.toSun(amount)
            sql = self.get_resource("insert_tip.sql")
            self.execute_global_sql(sql, from_user_id, to_user_id, sent_amount)
        except Exception as e:
            logging.error(e)

            if str(e) == "key 'transaction' not in send result":
                msg = f"{emo.ERROR} Balance not sufficient. Try removing fee of `{con.TRX_FEE}` TRX"
                update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
                logging.error(f"{msg} - {update}")
            else:
                update.message.reply_text(f"{emo.ERROR} {repr(e)}")

    def _remove_msg(self, bot, job):
        param_lst = job.context.split("_")
        chat_id = param_lst[0]
        msg_id = param_lst[1]

        try:
            logging.info(f"Removing {self.get_name()}-message (chat_id {chat_id} msg_id {msg_id})")
            bot.delete_message(chat_id=chat_id, message_id=msg_id)
            logging.info(f"Removed {self.get_name()}-message (chat_id {chat_id} msg_id {msg_id})")
        except Exception as e:
            msg = f"Not possible to remove {self.get_name()}-message (chat_id {chat_id} msg_id {msg_id}): {e}"
            logging.error(msg)
