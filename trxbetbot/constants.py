import os

# Default transaction fee
TRX_FEE = 0.1
# Default fee limit
TRX_FEE_LIMIT = 2

# Project folders
DIR_SRC = os.path.basename(os.path.dirname(__file__))
DIR_TEM = "templates"
DIR_RES = "resources"
DIR_PLG = "plugins"
DIR_CFG = "config"
DIR_LOG = "logs"
DIR_DAT = "data"
DIR_TMP = "temp"

# Project files
FILE_DAT = "global.db"
FILE_CFG = "config.json"
FILE_TKN = "token.json"
FILE_TRX = "wallet.json"
FILE_LOG = "trxbetbot.log"

# Max Telegram message length
MAX_TG_MSG_LEN = 4096
