import traceback
import sys

from lastwill.telegram_bot.models import BotSub
from lastwill.telegram_bot.main_bot import bot
from celery import shared_task
from lastwill.settings import NETWORKS
from lastwill.contracts import models


@shared_task
def send_message_to_subs(message='', contract_id=None, **kwargs):
    if contract_id:
        info = extract_info(contract_id)
        message += text_from_data(info)
        kwargs = {'disable_web_page_preview':True, 'parse_mode':'html'}

    subs = BotSub.objects.all()
    for sub in subs:
        try:
            bot.bot.send_message(sub.chat_id, message, **kwargs)
        except Exception:
            bot.bot.send_message(sub.chat_id, 'an exception occurred while sending the message')
            print('\n'.join(traceback.format_exception(*sys.exc_info())), flush=True)
            print(message, flush=True)


def extract_info(contract_id):
    output = {}
    contract = models.Contract.objects.get(id=contract_id)
    details = contract.get_details()
    eth_contracts = contract.ethcontract_set.all()
    hashes = [eth_contract.tx_hash for eth_contract in eth_contracts]
    link = NETWORKS[contract.network.name]['link_tx']

    contract_type = contract.get_all_details_model()[contract.contract_type]
    user_id = contract.user.id
    contract_options = []
    for option in ['white_label', 'authio', 'verification']:
        try:
            contract_options.append(getattr(details, option))
        except AttributeError:
            pass

    output['contract_id'] = contract_id
    output['network'] = contract.network.name
    output['contract_type'] = contract_type
    output['contract_options'] = contract_options if contract_options else 'no options'
    output['user_id'] = user_id
    output['links'] = [f'\n{link.format(tx=hsh)}' for hsh in hashes]

    return output


def text_from_data(data):
    text =  f"""<p>deployed contract {data["contract_id"]} on {data["network"]}<br>
                with {data["contract_type"]} and {data["contract_options"]}<br>
                by {data["user_id"]}</p><br>"""

    hyperlink = '<a href="{url}">{text}</a><br>'
    for idx, link in enumerate(data['links']):
        text += hyperlink.format(url=link, text=f'tx{idx}')
    return text
