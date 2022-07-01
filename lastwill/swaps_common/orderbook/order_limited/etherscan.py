import logging

import requests

from .consts import ETHERSCAN_API_KEY, ETHERSCAN_API_URL


def get_gas_price() -> int:
    """
    Get gas price from etherscan api.
    Returns gas price for average speed : int.
    """

    response = requests.get(
        "{url}?module=gastracker&action=gasoracle&apikey={api_key}".format(
            url=ETHERSCAN_API_URL,
            api_key=ETHERSCAN_API_KEY,
        )
    ) \
    .json()

    try:
        result = int(response['result']['FastGasPrice'])

        return result
    except (KeyError, Exception):
        logging.warning(f'Unable to get gas from Etnerscan.io.\nDescription: \n{response}.')
        print(f'Unable to get gas from Etnerscan.io.\nDescription: \n{response}.')
