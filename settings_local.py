WALLET_ADDRESS = ''

PRIVATE_KEY = ''

ETH_PROVIDER_URL = ''

BSC_PROVIDER_URL = ''
ETH_SWAP_CONTRACT_ADDRESS = ''
BSC_SWAP_CONTRACT_ADDRESS = ''
SWAP_BACKEND_URL = ''
import logging

MIDDLEWARE = [
    # 'lastwill.profile.middleware.session_middleware.SessionHostDomainMiddleware',
    # 'lastwill.profile.middleware.session_middleware.CrossDomainSessionMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

CELERY_EMAIL_TASK_CONFIG = {
    'queue': 'lastwill',
}


#EMAIL_BACKEND = 'djcelery_email.backends.CeleryEmailBackend'
#EMAIL_HOST = 'smtp.gmail.com'
#EMAIL_HOST_USER = 'fortestddg@gmail.com'
#EMAIL_HOST_PASSWORD = '1MODbBA0G1cQyrx3'
#EMAIL_PORT = 587

DEFAULT_SUPPORT_PASSWORD = 'ZAQ!2wsx'
EMAIL_HOST = 'smtp.yandex.com'
EMAIL_HOST_USER = 'strenk.m@mywish.io'
EMAIL_HOST_PASSWORD = 'izqkkyigntqknltf'
EMAIL_PORT = 587
EMAIL_USE_TLS = True

EMAIL_HOST_SWAPS = 'smtp.yandex.com'
EMAIL_HOST_USER_SWAPS = 'strenk.m@mywish.io'
EMAIL_HOST_PASSWORD_SWAPS = 'izqkkyigntqknltf'
#EMAIL_HOST_PASSWORD_SWAPS = 'izqkkyigntqknltf'
EMAIL_PORT_SWAPS = 465
EMAIL_USE_TLS_SWAPS = True

ALLOWED_HOSTS = [
    '127.0.0.1',
    'dev.mywish.io',
    'dev2.mywish.io',
    'trondev.mywish.io',
    'newlp.mywish.io',
    'new.mywish.io',
    'devswaps.mywish.io',
    'devwaves.mywish.io',
    'devprot.mywish.io',
]

D_BACKEND_ADDRESS = "0x4556443Af4D084A18CDaCa6A75C504c61E01737A"

DEFAULT_FROM_EMAIL = 'strenk.m@mywish.io'
DEFAULT_TO_EMAIL = 'strenk.m@mywish.io'
DEFAULT_SUPPORT_EMAIL = 'team@mywish.io'
#DEFAULT_TO_EMAIL = 'fortestddg@gmail.com'
#DEFAULT_TO_EMAIL = 'fortestddg@gmail.com'

ORACLIZE_PROXY = '0xC282Ef8e7d33111Dc365eEc25aea3f0BEfFE77fe' # ROPSTEN
ORACLIZE_PROXY = '0x43DaAc89DDfa322222650cBc7e87d24F87E4fFcE' # KOVAN

SECRET_KEY = 'eufz^slmya+a*4rnxbrad1dlci(@+9xi_u&!%te$6p-c+l$mbi'
KEY_ID = ''

# DEPLOY_ADDR = '0x4556443af4d084a18cdaca6a75c504c61e01737a'


SITE_ID = 2

CONTRACTS_DIR = '/home/contract'

NETWORKS = {
    'ETHEREUM_MAINNET': {
        'host': '127.0.0.1', 
        'port': '8545',
        'node_url': 'https://ropsten.infura.io/v3/68c4d45e98d842da9ad152b3d0f2e7e2',
        'address': '0x4556443af4d084a18cdaca6a75c504c61e01737a',
        'checksummed_address': '0x4556443Af4D084A18CDaCa6A75C504c61E01737A',
        'queue': 'notification-ethereum',
        'is_free': False,
        'link_address': 'https://etherscan.io/address/{address}',
        'link_tx': 'https://etherscan.io/tx/{tx}',
        'infura_subdomain': 'ropsten',
        'infura_project_id': 'c139df87547b41c9b3b3a1c148913286',
        'provider': 'infura',
    },
    'ETHEREUM_ROPSTEN': {
        #'host': 'data-seed-prebsc-1-s1.binance.org',
        #'host': '127.0.0.1',
        #'port': '8545',
        'node_url':'https://speedy-nodes-nyc.moralis.io/ad539bf41a744458eb7b73e6/eth/ropsten', #'https://ropsten.infura.io/v3/68c4d45e98d842da9ad152b3d0f2e7e2',
        'address': '0xfab506c694b6e1aa96d7648c6f688b23002bf683',
        'queue': 'notification-ropsten',
        'is_free': True,
        'link_address': 'https://ropsten.etherscan.io/address/{address}',
        'link_tx': 'https://ropsten.etherscan.io/tx/{tx}',
        #'infura_subdomain': 'ropsten',
        #'infura_project_id': 'c139df87547b41c9b3b3a1c148913286',
        'provider': 'parity',
    },
#    'RSK_MAINNET': {'host': '127.0.0.1', 'port': '4444', 'address': '0x4556443af4d084a18cdaca6a75c504c61e01737a', 'queue': 'notification-rsk', 'is_free': False, 'link_address': 'https://explorer.rsk.co/addr/{address}', 'link_tx': 'https://explorer.rsk.co/tx/{tx}'},
#    'RSK_TESTNET': {'host': '127.0.0.1', 'port': '4444', 'address': '0xfab506c694b6e1aa96d7648c6f688b23002bf683', 'queue': 'notification-rsk-testnet', 'is_free': True, 'link_address': 'https://explorer.testnet.rsk.co/addr/{address}', 'link_tx': 'https://explorer.testnet.rsk.co/tx/{tx}'},
#    'RSK_MAINNET_FOR_GATEWAY': {'host': '127.0.0.1', 'port': '4444', 'address': '0x2f32def55ee639ddab70f4d78367d1c6ed314392', 'queue': 'notification-rsk-fgw'},
#    'RSK_TESTNET_FOR_GATEWAY': {'host': '127.0.0.1', 'port': '4444', 'address': '0x2f32def55ee639ddab70f4d78367d1c6ed314392', 'queue': 'notification-rsk-testnet-fgw'},
    'NEO_MAINNET': {
         'is_free': False, 'queue': 'notification-neo',
        'host': '127.0.0.1', 'port': '20337',
        'link_address': 'http://neoscan.mywish.io/address/{address}',
        'link_tx': 'http://neoscan.mywish.io/transaction/{tx}',
        'address':'ARYM9jydXic4vk8Fb62yd3YjYgzv2vkjw8'
    },
    'NEO_TESTNET': {
        'is_free': True, 'queue': 'notification-neo-testnet',
        'host': '127.0.0.1', 'port': '20332',
        'link_address': 'http://neoscan.mywish.io/address/{address}',
        'link_tx': 'http://neoscan.mywish.io/transaction/{tx}',
        'address': 'ANiYsMFutPjP9hNrpYrJWVKoSfcxwbyFf7'
    },
    'EOS_MAINNET': {
        'is_free': False, 'queue':'notification-eos',
        'host':'jungle3.cryptolions.io', 'port': '80',
        'wallet': 'leha', 'address': 'mywishtoken4',
        'eos_password': 'PW5HzUQPwjdZQHXyhX98zHA7TySWpLQ5nDfnoScF8Z4kYW3gLu6P2',
        'link_address': 'https://eospark.com/MainNet/account/{address}',
        'link_tx': 'https://eospark.com/MainNet/tx/{tx}', 
        'token_address': 'mywishtoken4', 'pub':'EOS6bfZpKqCXFD2CFD8gcA4PVXBzT4sFZ5sabVM4KRFLW1y5HcywQ',
        'stake_cpu': '1.0000 EOS', 'stake_net': '0.2000 EOS', 'ram': '300',
        'airdrop_address': 'air1mywishio', 'tokensfather': 'tokenfather2'
    },
    'EOS_TESTNET': {
        'is_free': True, 'queue':'notification-eos-testnet',
        'host': 'jungle3.cryptolions.io', 'port': '80',
        'wallet': 'leha', 'address': 'mywishtoken3',
        'eos_password': 'PW5HzUQPwjdZQHXyhX98zHA7TySWpLQ5nDfnoScF8Z4kYW3gLu6P2',
        'link_address': 'https://eospark.com/Jungle/account/{address}',
        'link_tx': 'https://eospark.com/Jungle/tx/{tx}',
        'token_address': 'mywishtoken3', 'pub':'EOS6bfZpKqCXFD2CFD8gcA4PVXBzT4sFZ5sabVM4KRFLW1y5HcywQ',
        'stake_cpu': '10.0000 EOS', 'stake_net': '10.0000 EOS', 'ram': '300',
        'airdrop_address': 'mywishairdro', 'tokensfather': 'tokenfather2'
    },
    'BTC_MAINNET': {'is_free': False, 'queue': 'notification-btc', 'host': '127.0.0.1', 'port': '8332'},
    'BTC_TESTNET': {'is_free': True, 'queue': 'notification-btc-testnet', 'host': '127.0.0.1', 'port': '8332'},
    'TRON_MAINNET':{
        'is_free': False, 'queue': 'notification-tron-mainnet',
        'address': 'TD98AmVb55umS9tCU7bynmKD6xPHvGqzzW',
        'private_key': 'a89f7870a62efb4e44e32ad245d8af5527a2108100e7ba3eccce5fc51b5e520e',
        'host': 'http://127.0.0.1:8054',
        'host': 'https://api.shasta.trongrid.io',
        'check_address': 'TYy62fXYuVGbznyRYgZ3dHNfCt4TEBrAQV',
        'check_private_key': '69e27add26f549fea92274425deb8f029c26b6c5c5ce097df3664831297f808e',
        'link_address': 'https://shasta.tronscan.org/#/address/{address}',
        'link_tx': 'https://shasta.tronscan.org/#/transaction/{tx}',
    },
    'TRON_TESTNET': {
        'is_free': True, 'queue': 'notification-tron-testnet',
        'address': 'TD98AmVb55umS9tCU7bynmKD6xPHvGqzzW',
        'private_key': 'a89f7870a62efb4e44e32ad245d8af5527a2108100e7ba3eccce5fc51b5e520e',
         # 'host': 'http://127.0.0.1:8054',
        'host': 'https://api.shasta.trongrid.io',
        'check_address': 'TYy62fXYuVGbznyRYgZ3dHNfCt4TEBrAQV',
        'check_private_key': '69e27add26f549fea92274425deb8f029c26b6c5c5ce097df3664831297f808e',
        'link_address': 'https://shasta.tronscan.org/#/address/{address}',
        'link_tx': 'https://shasta.tronscan.org/#/transaction/{tx}',
    },
    'WAVES_MAINNET': {
        'is_free': False, 'queue': 'notification_waves_testnet',
        'address': '3N4QhS7pSSnbPRkSTf54H4reDa5XaPLJNHE',
        'private_key': '2fXfT1SQeX6nPcf3M469QhY84gWjd4SKs3FTk2sF5JRE',
        'public_key': 'DPL7Ku6LTS8T3Ti3iFADsk3Xd92jtnWfamZKy3ND87pP',
        'host': 'testnode1.wavesnodes.com', 'port': '',
        'type': 'testnet',
        'link_address': 'https://wavesexplorer.com/address/{address}',
        'link_asset': 'https://wavesexplorer.com/assets/{asset}',
        'link_tx': 'https://wavesexplorer.com/tx/{tx}'
    },
    'WAVES_TESTNET':{
        'is_free': True, 'queue': 'notification_waves_testnet',
        'address': '3N4QhS7pSSnbPRkSTf54H4reDa5XaPLJNHE',
        'private_key': '2fXfT1SQeX6nPcf3M469QhY84gWjd4SKs3FTk2sF5JRE',
        'public_key': 'DPL7Ku6LTS8T3Ti3iFADsk3Xd92jtnWfamZKy3ND87pP',
        'host': 'testnode1.wavesnodes.com', 'port': '',
        'type': 'testnet',
        'link_address': 'https://wavesexplorer.com/testnet/address/{address}',
        'link_asset': 'https://wavesexplorer.com/testnet/assets/{asset}',
        'link_tx': 'https://wavesexplorer.com/testnet/tx/{tx}'
    },
    'BINANCE_SMART_MAINNET': {
        #'host': '127.0.0.1',
        #'port': '8545',
        'node_url': 'https://data-seed-prebsc-1-s1.binance.org:8545',
        'address': '0x519a3ed101CFff238cdFa6cb56DbDF61ef588050',
        'checksummed_address': '0x519a3ed101CFff238cdFa6cb56DbDF61ef588050',
        'queue': 'notification-binance-smart-mainnet',
        'is_free': False,
        'link_address': 'https://testnet.bscscan.com/address/{address}',
        'link_tx': 'https://testnet.bscscan.com/tx/{tx}',
        'provider': 'parity',
    },
    'BINANCE_SMART_TESTNET': {
        #'host': 'data-seed-prebsc-1-s1.binance.org',
        #'host': '127.0.0.1',
        #'port': '8545',
        'node_url': 'https://speedy-nodes-nyc.moralis.io/ad539bf41a744458eb7b73e6/bsc/testnet', #'https://data-seed-prebsc-2-s2.binance.org:8545',
        'address': '0x519a3ed101CFff238cdFa6cb56DbDF61ef588050',
        'queue': 'notification-binance-smart-testnet',
        'is_free': True,
        'link_address': 'https://testnet.bscscan.com/address/{address}',
        'link_tx': 'https://testnet.bscscan.com/tx/{tx}',
        'provider': 'parity',
    },
    'MATIC_MAINNET': {
        'address': '0x799f216b53CEA90458E65448B35095De96043573',
        'queue': 'notification-matic',
        'node_url': 'https://speedy-nodes-nyc.moralis.io/307e73ae757a9b3501a21bd5/polygon/mumbai',
        #'node_url': 'https://rpc-mumbai.matic.today',
        'is_free': False,
        'link_address': 'https://mumbai.polygonscan.com/address/{address}',
        'link_tx': 'https://mumbai.polygonscan.com/tx/{tx}',
        'provider': 'parity',
    },
    'MATIC_TESTNET': {
        'address': '0x8Bd2b82C90242eBB28e721b8ddD74C5e5C9Cf928',
        'queue': 'notification-matic-testnet',
        'node_url': 'https://speedy-nodes-nyc.moralis.io/307e73ae757a9b3501a21bd5/polygon/mumbai',
        #'node_url': 'https://rpc-mumbai.matic.today',
        #'node_url': 'https://alfajores-forno.celo-testnet.org',
        'is_free': True,
        'link_address': 'https://mumbai.polygonscan.com/address/{address}',
        'link_tx': 'https://mumbai.polygonscan.com/tx/{tx}',
        'provider': 'parity',
    },
   'XINFIN_MAINNET': {
	'address': '0x4556443af4d084a18cdaca6a75c504c61e01737a',
        'queue': 'notification-xinfin',
        'node_url': 'https://rpc.xinfin.network/',
        'is_free': False,
        'link_address': 'https://explorer.xinfin.network/addr/{address}',
        'link_tx': 'https://explorer.xinfin.network/tx/{tx}',
        'provider': 'parity',
    },
   'XINFIN_TESTNET': {
	'address': '0x67E7fd91d1a2cC465e153064d4A5dF835E173b7a',
        'queue': 'notification-xinfin',
        'node_url': 'https://rpc.xinfin.network/',
        'is_free': False,
        'link_address': 'https://xinfin.network/#stats/address/{address}',
        'link_tx': '/tx/{tx}',
        'provider': 'parity',
    },
   'HECOCHAIN_MAINNET': {
	'address': '0x4556443af4d084a18cdaca6a75c504c61e01737a',
	'queue': 'notification-hecochain',
        'node_url': 'https://http-testnet.hecochain.com',
        'is_free': False,
        'link_address': 'https://hecoinfo.com/address/{address}',
        'link_tx': 'https://hecoinfo.com/tx/{tx}',
        'provider': 'parity',
   },
   'HECOCHAIN_TESTNET': {
        'address': '0x4556443af4d084a18cdaca6a75c504c61e01737a',
        'queue': 'notification-hecochain-testnet',
        'node_url': 'https://rpc.testnet.moonbeam.network', #'https://rpc-testnet.kcc.network', # 'https://http-testnet.hecochain.com',
        'is_free': True,
        'link_address': 'https://testnet.hecoinfo.com/address/{address}',
        'link_tx': 'https://testnet.hecoinfo.com/tx/{tx}',
        'provider': 'parity',
   },
    'MOONRIVER_MAINNET': {
        'address': '0x4556443af4d084a18cdaca6a75c504c61e01737a',
        'checksummed_address': '0x4556443Af4D084A18CDaCa6A75C504c61E01737A',
        'queue': 'notification-moonriver-mainnet',
        'node_url': 'https://rpc.moonriver.moonbeam.network',
        'is_free': False,
        'link_address': 'https://moonriver.subscan.io/account/{address}',
        'link_tx': 'https://moonriver.subscan.io/extrinsic/{tx}',
        'provider': 'parity',
    },

}

FACEBOOK_CLIENT_ID = '438113386623173'
FACEBOOK_CLIENT_SECRET = '5c19a7af39efd04af84d0c2b551c9efd'

FACEBOOK_CLIENT_IDS = {
     'dev.mywish.io': '438113386623173',
     'devswaps.mywish.io': ''
    }

FACEBOOK_CLIENT_SECRETS = {
     'dev.mywish.io': '5c19a7af39efd04af84d0c2b551c9efd',
     'devswaps.mywish.io': ''
    }

SWAPS_ORDERBOOK_QUEUE = 'notification-swaps-mainnet'
SWAPS_WIDGET_HOST = 'dev.mywish.io'
SWAPS_WIDGET_TOKEN = '6e7c679c-1500-41a1-83f5-3c2bde451ba7'

SOLC = '/bin/solc --optimize --combined-json abi,bin --allow-paths={}'
EMAIL_FOR_POSTPONED_MESSAGE = 'ephdtrg@gmail.com'

BITCOIN_URLS ={
    'main': 'http://bitcoin:btcpwd@127.0.0.1:18332/',
    'test': 'http://bitcoin:btcpwd@127.0.0.1:18332/'
}

ROOT_PUBLIC_KEY = 'xpub68EMpFBFnZJqvo94XQReKh13JjVqx9gXvWncep1TYpYArn9Pf7a4HHdfheWyegaz5SPM2fequYDENAJz3eUdDSNaAZB4T6XN3nkb56g2tFv'
ROOT_PUBLIC_KEY_EOSISH = 'xpub69kMaJ8hj8mBhFWFxvJ3zLVAZeNPzUe7R6YMf6imKqdGvvJ9DL6YYcXGiQZDXt2JaQJhSPxQHZFEoWzznqh4Qxk8VxJZV5xUxnNXg3uzQzR'
ROOT_PUBLIC_KEY_TRON = 'xpub69aQX7pd36mZCdyzFktV7c5X87Z3Y3Ayxzi4rLUS7V5KDvVAPs5APjnq7necc2HGvzUogfkgrzRfNdEW6KGEeW6kvwp6Lgj9yDT5wLDjnu8'
ROOT_PUBLIC_KEY_SWAPS = 'xpub67wh9yU5hNdXAUu7fhLwUZdgmv4K4NcFaPCvMLE28ot4FoqknL7eDoL1MhkkuR5iDnWK84MJMjTcMKcW1LrnFD54BmNDGL1h2tFHVTz8Xz8'
ROOT_PUBLIC_KEY_PROTECTOR = 'xpub69gGegjdfDiDEtB5xbNcq4nfxkyEAMwTiZQUcpojQc3mNYCPqFYpL3e3KokLLci7BwZ1gFh9NYUgD4jfTQd1RtPLTVMtWYczekG7iDoy3PC'


EOS_PASSWORD='PW5JC5vRsJRyj77raFT7TerxvancT4WSVMbNeM3kRmDSh32AGDZ84'

test_logger = logging.getLogger('django.request')

SESSION_COOKIE_NAME = 'dev_sessionid'

EOSPARK_API_KEY = '3f73b4273a6fcaf3ae8e2fd015fc85c9'
ETHERSCAN_API_KEY = 'R2RZXP9BQSDC7Y12QY7EHKGTBGF3FRGWIW'
COINMARKETCAP_API_KEYS = [
    '4578c9a0-c6b3-47ed-a77d-8339fed26342',
    '15ab92a7-ea1c-41ec-84e6-214ccfb291b8',
    '1a75ec03-bdda-4d00-8c55-c991567784d7',
]
CRYPTOCOMPARE_API_KEY='7b73792c21f2e6fc98421165d587b0816ba03a42985d6b93015d360c7bd925e7'


MY_WISH_URL = 'dev2.mywish.io'
EOSISH_URL = 'deveos.mywish.io'
TRON_URL = 'trondev.mywish.io'
SWAPS_URL = 'devswaps.mywish.io'
WAVES_URL = 'devwaves.mywish.io'
TOKEN_PROTECTOR_URL = 'devprot.mywish.io'
DUCATUSX_URL = 'trondev.mywish.io'
RUBIC_EXC_URL = 'devswaps.mywish.io'
RUBIC_FIN_URL = 'devswaps.mywish.io'
SITE_PROTOCOL = 'http'

EOS_TEST_URL_ENV = '/home/pydaemon/eos_autotest/venv/bin/python3.6'
EOS_TEST_URL = '/home/pydaemon/eos_autotest/contracts/eosiotokenstandalone/test/unittest_tokenstandalone.py'
EOS_TEST_FOLDER = '/home/pydaemon/eos_autotest/contracts/eosiotokenstandalone/'
EOS_TEST_ICO_FOLDER = '/home/pydaemon/eos_autotest/contracts/eosio-crowdsale/'
EOS_TEST_ICO_URL = '/home/pydaemon/eos_autotest/contracts/eosio-crowdsale/unittest_crowdsale.py'

#BINANCE_PAYMENT_ADDRESS = 'tbnb1pxwzr62lhdn27mpkdauuf7r4f56mkgmn2zznkc'
BINANCE_PAYMENT_ADDRESS = 'tbnb1lfvv3p03tu8kqdqhx2cz4muyhm87qhnpm8cqvx'
BINANCE_PAYMENT_PASSWORD = 'a9e3daf15978b037145e58a4172ed84adcdf3e66268a3e16d8c422448462c058'
COLD_BNB_ADDRESS = 'tbnb1munpv2nr27s9fzs4eczfyyzwqw8md3g4tcwldw'

COLD_WISH_ADDRESS = '0x2246Bf20f536cbf9ab9a7bC8B3518276Ae40b2F6'
COLD_EOSISH_ADDRESS = 'eosishfreeze'
#COLD_TRON_ADDRESS = 'TPbuLNEpxySW6JfkdcuDSxuMuEEgYG4iK4'
#UPDATE_TRON_ADDRESS = 'TBUJkpfdmDTbbCwtpM3SNGG7RkQ9HUENt3'
#TRON_COLD_PASSWORD = '1953dfd807865bb4065d0adc0423d7848ba83edfdff616c24a6d790ccb0f114b'
COLD_TRON_ADDRESS = 'TQwtHyw5NZ49BSg1Rq6ujKB4dqPz3TAdg5'
TRON_ADDRESS = 'TPYgnEkkA7E6RofKNHxfJwuFAFSzqphuPh'
UPDATE_TRON_ADDRESS = 'TR9ihqtadLkYCxMgcmsJsvoWKUBdR9biSR'
TRON_COLD_PASSWORD = '4a384fbb9f139f566fca6a99d2155cd1f40c72d5190dec9e6acbb9ff5b34b3ab'
UPDATE_WISH_ADDRESS = '0x5f7492ee271ee1cb5ab78a1c4e71230415c6aac2'
UPDATE_EOSISH_ADDRESS = 'holdereosish'
EOS_COLD_ABI = 'eosishfreez2'
#MYWISH_ADDRESS = '0xa9CcA3bC3867C8D833682AF3Fec46Ad5bdF1A1b8'
MYWISH_ADDRESS = '0xD459Bc1d8c2c7fD9B02574D7b9d69843355ee0DD'
FREEZE_THRESHOLD_EOSISH = 10000 * 10 ** 4
FREEZE_THRESHOLD_WISH = 100 * 10 ** 18
FREEZE_THRESHOLD_BWISH = 1000 * 10 ** 18

FREEZE_THRESHOLD_TRONISH = 450 * 10 ** 6
NETWORK_SIGN_TRANSACTION_WISH = 'ETHEREUM_ROPSTEN'
NETWORK_SIGN_TRANSACTION_EOSISH = 'EOS_TESTNET'
NETWORK_SIGN_TRANSACTION_BWISH = 'testnet'
COLD_TOKEN_SYMBOL_EOS = 'EOSISH'
COLD_TOKEN_SYMBOL_BNB = 'WISH-1EF'


#AUTHIO_EMAIL = 'ephdtrg@gmail.com'
AUTHIO_EMAIL = 'khalitov.yulian@yandex.ru'
SUPPORT_EMAIL = 'khalitov.yulian@yandex.ru'
SWAPS_MAIL = 'fortestddg@gmail.com'
SWAPS_SUPPORT_MAIL = 'support@mywish.io'
CMC_TOKEN_UPDATE_MAIL = 'ephdtrg@gmail.com'

DEFAULT_IMAGE_LINK = 'https://raw.githubusercontent.com/MyWishPlatform/etherscan_top_tokens_images/master/fa-empire.png'

LASTWILL_ALIVE_TIMEOUT = 60 * 30

TRON_REPLENISH_ACCOUNT = {
    'address': 'TFe73tbLyg8kC54F9RZiTvvU5TQQkdcNoj',
    'private_key': '88cf87ca09d9b11ffcb8b560514dc4b52845c3adbf281ffafcef4ced005b630b'
} 

TRON_REPLENISH_CHECK_ACCOUNT = {
    'address': 'TKDP9qQCQKDaMTqeMY756HxW7V9xo1uRBu',
    'private_key': '56ce03c16134afb0301002cc2822e74a166abff32ffe53968938e172ea12b50b'
} 

TRON_NODE = 'http://127.0.0.1:8054'

TRX_FREEZE_TIMEOUT = 60 * 60 * 73
TRX_FREEZE_AMOUNT = 100

SIGNER = 'http://127.0.0.1:666/sign/'

import warnings
warnings.filterwarnings(
    'ignore', r"DateTimeField .* received a naive datetime",
    RuntimeWarning, r'django\.db\.models\.fields',
)

'''
TRON_BALANCE_API_URL = {
    'testnet': 'https://api.shasta.trongrid.io/v1/accounts/{address}',
    'mainnet': 'https://api.trongrid.io/v1/accounts/{address}',
}

EOS_ACCOUNT_API_URL = {
    'testnet': 'https://jungle2.cryptolions.io/v1/chain/get_account',
    'mainnet': 'https://eos.greymass.com/v1/chain/get_account',
}
'''

TRON_BALANCE_API_URL = {
    'testnet': 'https://api.shasta.trongrid.io/v1/accounts/{address}',
    'mainnet': 'https://api.shasta.trongrid.io/v1/accounts/{address}',
}

EOS_ACCOUNT_API_URL = {
    'testnet': 'https://jungle2.cryptolions.io/v1/chain/get_account',
    'mainnet': 'https://jungle2.cryptolions.io/v1/chain/get_account',
}

DEBUG = True

GAS_API_URL = ''

SPEEDLVL = ''

ROOT_EXT_KEY = 'xprv9s21ZrQH143K3GjWN51v8vFJ1jm8YF4JnmJxLK3Th4QWvaBCkLsaDwYe3L153bHrd3JcoTDmPypdBrVmUVYCoW8XoR9DjxQ4JTtiytRb2jZ'

NEO_CLI_DIR = '/home/backend/neo-cli-backend/neo-cli'

MW_COPYRIGHT = """
/*
 * This file was generated by MyWish Platform (https://mywish.io/)
 * The complete code could be found at https://github.com/MyWishPlatform/
 * Copyright (C) 2021 MyWish
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this program. If not, see <http://www.gnu.org/licenses/>.
 */

"""

bot_token = '1947495553:AAEQSFQQive9S7W4tQ3MNj9LecAwLuJJduQ'

WISH_GIFT_AMOUNT = 250
SEND_GIFT_MAIL_DAYS = 1
