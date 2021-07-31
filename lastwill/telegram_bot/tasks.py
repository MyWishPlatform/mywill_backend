import traceback
import sys

from lastwill.telegram_bot.models import BotSub
from lastwill.telegram_bot.main_bot import bot
from celery_config import app
from lastwill.settings import NETWORKS


@app.task
def send_message_to_subs(message, contract=None):
    if contract:
        message += gen_links(contract)

    subs = BotSub.objects.all()
    for sub in subs:
        try:
            bot.bot.send_message(sub.chat_id, message)
        except Exception:
            print('\n'.join(traceback.format_exception(*sys.exc_info())), flush=True)


def gen_links(contract):
    out = ''
    eth_contracts = contract.eth_contract_set.all()
    hashes = [eth_contract.tx_hash for eth_contract in eth_contracts]
    link = NETWORKS[contract.network.name]['link_tx']
    for hsh in hashes:
        out += f'\n{link.format(tx=hsh)}'
    return out
