from lastwill.contracts.submodels.airdrop import AbstractContractDetailsAirdrop
from lastwill.contracts.submodels.common import *
from lastwill.consts import NET_DECIMALS, CONTRACT_PRICE_USDT
from lastwill.settings import BSC_ATTEMPTS_COUNT, BSC_ATTEMPTS_COOLDOWN


@contract_details('Binance Airdrop')
class ContractDetailsBinanceAirdrop(AbstractContractDetailsAirdrop):
    @staticmethod
    def calc_cost(kwargs, network):
        if NETWORKS[network.name]['is_free']:
            return 0
        # return 0.5 * 10**18
        return CONTRACT_PRICE_USDT['BINANCE_AIRDROP'] * NET_DECIMALS['USDT']

    @classmethod
    def min_cost(cls):
        network = Network.objects.get(name='BINANCE_SMART_MAINNET')
        cost = cls.calc_cost({}, network)
        return cost

    @blocking
    @postponable
    def deploy(self, eth_contract_attr_name='eth_contract_token'):
        if self.contract.state not in ('CREATED', 'WAITING_FOR_DEPLOYMENT'):
            print('launch message ignored because already deployed', flush=True)
            take_off_blocking(self.contract.network.name)
            return
        self.compile(eth_contract_attr_name)
        eth_contract = getattr(self, eth_contract_attr_name)
        tr = abi.ContractTranslator(eth_contract.abi)
        arguments = self.get_arguments(eth_contract_attr_name)
        print('arguments', arguments, flush=True)
        eth_contract.constructor_arguments = binascii.hexlify(
            tr.encode_constructor_arguments(arguments)
        ).decode() if arguments else ''
        eth_int = EthereumProvider().get_provider(network=self.contract.network.name)
        address = NETWORKS[self.contract.network.name]['address']

        for attempt in range(BSC_ATTEMPTS_COUNT):
            print(f'attempt {attempt} to get a nonce', flush=True)
            try:
                nonce = int(eth_int.eth_getTransactionCount(address, "pending"), 16)
                break
            except Exception:
                print('\n'.join(traceback.format_exception(*sys.exc_info())), flush=True)
            time.sleep(BSC_ATTEMPTS_COOLDOWN)
        else:
            raise Exception(f'cannot get nonce with {BSC_ATTEMPTS_COUNT} attempts')

        print('nonce', nonce, flush=True)

        data = eth_contract.bytecode + (binascii.hexlify(
            tr.encode_constructor_arguments(arguments)
        ).decode() if arguments else '')
        print('data', data, flush=True)

        gas_price = ETH_COMMON_GAS_PRICES[self.contract.network.name] * NET_DECIMALS['ETH_GAS_PRICE']
        signed_data = sign_transaction(
            address, nonce, self.get_gaslimit(),
            self.contract.network.name, value=self.get_value(),
            contract_data=data, gas_price=gas_price
        )
        print('fields of transaction', flush=True)
        print('source', address, flush=True)
        print('gas limit', self.get_gaslimit(), flush=True)
        print('value', self.get_value(), flush=True)
        print('network', self.contract.network.name, flush=True)
        print('signed_data', signed_data, flush=True)

        for attempt in range(BSC_ATTEMPTS_COUNT):
            print(f'attempt {attempt} to send deploy tx', flush=True)
            try:
                tx_hash = eth_int.eth_sendRawTransaction('0x' + signed_data)
                break
            except Exception:
                print('\n'.join(traceback.format_exception(*sys.exc_info())), flush=True)
            time.sleep(BSC_ATTEMPTS_COOLDOWN)
        else:
            raise Exception(f'cannot send deploy tx with {BSC_ATTEMPTS_COUNT} attempts')

        eth_contract.tx_hash = tx_hash
        eth_contract.save()
        print('transaction sent', flush=True)
        self.contract.state = 'WAITING_FOR_DEPLOYMENT'
        self.contract.save()
