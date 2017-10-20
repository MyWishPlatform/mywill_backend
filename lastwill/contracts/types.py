from lastwill.settings import ORACLIZE_PROXY

def original_get_arguments(contract):
    return [
        contract.user_address,
        [h.address for h in contract.heir_set.all()],
        [h.percentage for h in contract.heir_set.all()],
        contract.check_interval,
        ORACLIZE_PROXY,
    ]

def wallet_get_arguments(contract):
    return [
        contract.user_address,
        [h.address for h in contract.heir_set.all()],
        [h.percentage for h in contract.heir_set.all()],
        contract.check_interval,
    ]

contract_types = [
    {
        'name': 'MyWish Original',
        'sol_path': '/var/www/contracts_repos/lastwill/contracts/LastWillOraclize.sol',
        'get_arguments': original_get_arguments,
        'details_model': 'contracts.ContractDetailsLastwill',
    },
    {
        'name': 'MyWish Wallet',
        'sol_path': '/var/www/contracts_repos/lastwill/contracts/LastWillWallet.sol',
        'get_arguments': wallet_get_arguments,
        'details_model': 'contracts.ContractDetailsLastwill',
    },
]
