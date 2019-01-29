MAX_WEI_DIGITS = len(str(2**256))
MAIL_NETWORK = {
    'ETHEREUM_MAINNET': 'Ethereum',
    'ETHEREUM_ROPSTEN': 'Ropsten (Ethereum Testnet)',
    'RSK_MAINNET': 'RSK',
    'RSK_TESTNET': 'RSK Testnet',
    'NEO_TESTNET': 'NEO Test Net',
    'NEO_MAINNET': 'NEO',
    'EOS_MAINNET': 'EOS',
    'EOS_TESTNET': 'EOS Testnet',
    'TRON_MAINNET': 'TRON',
    'TRON_TESTNET': 'TRON Testnet',
}

API_NETWORK = {
    'ETHEREUM_MAINNET': 'ETHEREUM_MAINNET',
    'ETHEREUM_ROPSTEN': 'ETHEREUM_TESTNET',
    'RSK_MAINNET': 'BITCOIN_MAINNET',
    'RSK_TESTNET': 'BITCOIN_TESTNET',
    'NEO_TESTNET': 'NEO_MAINNET',
    'NEO_MAINNET': 'NEO_TESTNET',
    'EOS_MAINNET': 'EOS_MAINNET',
    'EOS_TESTNET': 'EOS TESTNET',
    'TRON_MAINNET': 'TRON_MAINNET',
    'TRON_TESTNET': 'TRON_TESTNET',
}

CONTRACT_PRICE_ETH = {
    'AIRDROP': 0.5,
    'DEFFERED': 0.025,
    'ICO': 4.99,
    'TOKEN': 2.99,
    'TOKEN_AUTHIO': 5.99,
    'INVESTMENT_POOL': 0.5,
    'EOS_TOKEN': 2.99,
    'EOS_ICO': 5,
    'EOS_TOKEN_STANDALONE': 5,
}

CONTRACT_PRICE_EOS = {
    'EOS_TOKEN': 150,
    'EOS_ICO': 250,
    'EOS_TOKEN_STANDALONE': 190,
}

CONTRACT_PRICE_NEO = {
    'NO_STORAGE': 200,
    'WITH_STORAGE': 600,
}

CONTRACT_PRICE_TRON = {
    'TRON_TOKEN': 5,
    'TRON_GAME_ASSET': 0.5,
}

BRAND_REPORT_PRICE = 3

CONTRACT_GAS_LIMIT = {
    'AIRDROP': 3000000,
    'DEFFERED': 1700000,
    'ICO': 3200000,
    'TOKEN': 3200000,
    'INVESTMENT_POOL': 3000000,
    'LASTWILL_PAYMENT': 50000,
    'LASTWILL_COMMON': 600000,
}

NET_DECIMALS = {
    'ETH': 10 ** 18,
    'ETH_GAS_PRICE': 10 ** 9,
    'EOS': 10 ** 4,
    'WISH': 10 ** 18,
    'EOSISH': 10 ** 4,
    'BNB': 10 ** 18,
    'BTC': 10 ** 8
}

URL_STATS_CURRENCY_BODY = 'https://api.coinmarketcap.com/v1/ticker/'
URL_STATS_CURRENCY = {
    'MYWISH': URL_STATS_CURRENCY_BODY + "mywish/",
    'MYWISH_ETH': URL_STATS_CURRENCY_BODY + "mywish/?convert=ETH",
    'BTC': URL_STATS_CURRENCY_BODY + "bitcoin/",
    'EOS': URL_STATS_CURRENCY_BODY + "eos/",
    'ETH': URL_STATS_CURRENCY_BODY + "ethereum/",
    'EOSISH': "https://api.chaince.com/tickers/eosisheos/",
}

URL_STATS_ETH_QUERY = 'api?module=account&action=balance&address='
URL_STATS_BALANCE = {
    'NEO': 'http://neoscan.mywish.io/api/test_net/v1/get_balance/',
    'ETH': 'https://api.etherscan.io/' + URL_STATS_ETH_QUERY,
    'ETH_ROPSTEN': 'https://api-ropsten.etherscan.io/' + URL_STATS_ETH_QUERY,
}

ETH_MAINNET_ADDRESS = '0x1e1fEdbeB8CE004a03569A3FF03A1317a6515Cf1'
ETH_TESTNET_ADDRESS = '0x88dbD934eF3349f803E1448579F735BE8CAB410D'

LASTWILL_ALIVE_TIMEOUT = 60 * 60 * 24