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

CONTRACT_GAS_LIMIT = {
    'AIRDROP': 3000000,
    'DEFFERED': 1700000,
    'ICO': 3200000,
    'TOKEN': 3200000,
    'INVESTMENT_POOL': 3000000
}

NET_DECIMALS = {
    'ETH': 10**18,
    'EOS': 10**4
}