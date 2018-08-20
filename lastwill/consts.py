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

eos_config = """
#define ISSUER {address}
#define TOKEN {token_short_name}
#define DECIMALS {decimals}

#define WHITELIST {whitelist}

#define TRANSFERABLE {transferable}

#define RATE {rate}
#define RATE_PRECISION 100 

#define MIN_CONTRIB  {min_wei}
#define MAX_CONTRIB {max_wei}

#define SOFT_CAP_EOS  {soft_cap}
#define HARD_CAP_EOS {hard_cap}

#define START_DATE  {start_date}
#define FINISH_DATE {stop_date}
"""
