from lastwill.contracts.submodels.ico import AbstractContractDetailsICO
from lastwill.contracts.submodels.common import *
from lastwill.consts import NET_DECIMALS, CONTRACT_PRICE_USDT
from lastwill.settings import BSC_ATTEMPTS_COUNT, BSC_ATTEMPTS_COOLDOWN


@contract_details('Binance MyWish ICO')
class ContractDetailsBinanceICO(AbstractContractDetailsICO):
    eth_contract_token = models.ForeignKey(
        EthContract,
        null=True,
        default=None,
        related_name='binance_ico_details_token',
        on_delete=models.SET_NULL
    )
    eth_contract_crowdsale = models.ForeignKey(
        EthContract,
        null=True,
        default=None,
        related_name='binance_ico_details_crowdsale',
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
        return int(CONTRACT_PRICE_USDT['BINANCE_ICO'] * NET_DECIMALS['USDT'])

    def compile(self, eth_contract_attr_name='eth_contract_token'):
        print('ico_contract compile')
        if self.temp_directory:
            print('already compiled')
            return
        dest, preproc_config = create_directory(self, sour_path='lastwill/binance-ico-crowdsale/*')
        token_holders = self.contract.tokenholder_set.all()
        amount_bonuses = add_amount_bonuses(self)
        time_bonuses = add_time_bonuses(self)
        preproc_params = {'constants': {}}
        preproc_params['constants'] = add_token_params(
            preproc_params['constants'], self, token_holders,
            not self.is_transferable_at_once,
            self.continue_minting
        )
        preproc_params['constants'] = add_crowdsale_params(
            preproc_params['constants'], self, time_bonuses, amount_bonuses
        )
        if self.min_wei:
            preproc_params["constants"]["D_MIN_VALUE_WEI"] = str(
                int(self.min_wei))
        if self.max_wei:
            preproc_params["constants"]["D_MAX_VALUE_WEI"] = str(
                int(self.max_wei))

        test_crowdsale_params(preproc_config, preproc_params, dest)
        address = NETWORKS[self.contract.network.name]['address']
        preproc_params = add_real_params(
            preproc_params, self.admin_address,
            address, self.cold_wallet_address
        )
        with open(preproc_config, 'w') as f:
            f.write(json.dumps(preproc_params))
        if os.system(
                "/bin/bash -c 'cd {dest} && yarn compile-crowdsale'".format(
                    dest=dest)
        ):
            raise Exception('compiler error while deploying')
        with open(path.join(dest, 'build/contracts/TemplateCrowdsale.json'),
                  'rb') as f:
            crowdsale_json = json.loads(f.read().decode('utf-8-sig'))
        with open(path.join(dest, 'build/TemplateCrowdsale.sol'), 'rb') as f:
            source_code = f.read().decode('utf-8-sig')
        self.eth_contract_crowdsale = create_ethcontract_in_compile(
            crowdsale_json['abi'], crowdsale_json['bytecode'][2:],
            crowdsale_json['compiler']['version'], self.contract, source_code
        )
        if not self.reused_token:
            with open(path.join(dest, 'build/contracts/MainToken.json'),
                      'rb') as f:
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
    def deploy(self, eth_contract_attr_name='eth_contract_token'):
        if self.reused_token:
            eth_contract_attr_name = 'eth_contract_crowdsale'
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
