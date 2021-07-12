from lastwill.contracts.submodels.ico import AbstractContractDetailsToken
from lastwill.contracts.submodels.common import *
from lastwill.consts import NET_DECIMALS, CONTRACT_PRICE_USDT, VERIFICATION_PRICE_USDT, AUTHIO_PRICE_USDT, WHITELABEL_PRICE_USDT
from lastwill.settings import BSC_WEB3_ATTEMPTS


@contract_details('Binance Token contract')
class ContractDetailsBinanceToken(AbstractContractDetailsToken):
    eth_contract_token = models.ForeignKey(
        EthContract,
        null=True,
        default=None,
        related_name='binance_token_details_token',
        on_delete=models.SET_NULL
    )

    @classmethod
    def min_cost(cls):
        network = Network.objects.get(name='BINANCE_SMART_MAINNET')
        cost = cls.calc_cost({}, network)
        return cost

    @staticmethod
    def calc_cost(kwargs, network):
        if NETWORKS[network.name]['is_free']:
            return 0
        price = CONTRACT_PRICE_USDT['BINANCE_TOKEN']
        if 'authio' in kwargs and kwargs['authio']:
            price += AUTHIO_PRICE_USDT
        if 'verification' in kwargs and kwargs['verification']:
            price += VERIFICATION_PRICE_USDT
        if 'white_label' in kwargs and kwargs['white_label']:
            price += WHITELABEL_PRICE_USDT
        return price * NET_DECIMALS['USDT']

    def compile(self, eth_contract_attr_name='eth_contract_token'):
        print('standalone token contract compile')
        if self.temp_directory:
            print('already compiled')
            return
        dest, preproc_config = create_directory(self, sour_path='lastwill/binance-ico-crowdsale/*')
        token_holders = self.contract.tokenholder_set.all()
        preproc_params = {"constants": {"D_ONLY_TOKEN": True}}
        preproc_params['constants'] = add_token_params(
            preproc_params['constants'], self, token_holders,
            False, self.future_minting
        )
        test_token_params(preproc_config, preproc_params, dest)
        preproc_params['constants']['D_CONTRACTS_OWNER'] = self.admin_address
        with open(preproc_config, 'w') as f:
            f.write(json.dumps(preproc_params))
        if os.system('cd {dest} && yarn compile-token'.format(dest=dest)):
            raise Exception('compiler error while deploying')

        with open(path.join(dest, 'build/contracts/MainToken.json'), 'rb') as f:
            token_json = json.loads(f.read().decode('utf-8-sig'))
        with open(path.join(dest, 'build/MainToken.sol'), 'rb') as f:
            source_code = f.read().decode('utf-8-sig')
        self.eth_contract_token = create_ethcontract_in_compile(
            token_json['abi'], token_json['bytecode'][2:],
            token_json['compiler']['version'], self.contract, source_code
        )
        self.save()

    @blocking
    @postponable
    def deploy(self):
        return super().deploy(attempts=BSC_WEB3_ATTEMPTS)
