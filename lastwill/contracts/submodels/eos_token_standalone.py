from django.core.mail import send_mail

from lastwill.contracts.submodels.eos import *
from lastwill.json_templates import create_eos_token_sa_json
from lastwill.settings import EOS_TEST_URL, EOS_TEST_URL_ENV, EOS_TEST_FOLDER
from lastwill.consts import MAX_WEI_DIGITS, CONTRACT_PRICE_EOS, NET_DECIMALS, CONTRACT_PRICE_USDT

class ContractDetailsEOSTokenSA(CommonDetails):
    token_short_name = models.CharField(max_length=64)
    token_account = models.CharField(max_length=12)
    admin_address = models.CharField(max_length=12)
    decimals = models.IntegerField()
    eos_contract = models.ForeignKey(
            EOSContract,
            null=True,
            default=None,
            related_name='eos_token_sa_details',
            on_delete=models.SET_NULL,
    )
    temp_directory = models.CharField(max_length=36)
    maximum_supply = models.DecimalField(max_digits=MAX_WEI_DIGITS, decimal_places=0, null=True)

    def predeploy_validate(self):
        now = timezone.now()
        token_holders = self.contract.eostokenholder_set.all()
        for th in token_holders:
            if th.freeze_date:
                if th.freeze_date < now.timestamp() + 600:
                    raise ValidationError({'result': 1}, code=400)

    @classmethod
    def min_cost(cls):
        network = Network.objects.get(name='EOS_MAINNET')
        cost = cls.calc_cost({}, network)
        return cost

    @classmethod
    def min_cost_eos(cls):
        network = Network.objects.get(name='EOS_MAINNET')
        cost = cls.calc_cost_eos({}, network)
        return cost

    @staticmethod
    def calc_cost(kwargs, network):
        if NETWORKS[network.name]['is_free']:
            return 0
        return int(CONTRACT_PRICE_USDT['EOS_TOKEN_SA'] * NET_DECIMALS['USDT'])

    @staticmethod
    def calc_cost_eos(kwargs, network):
        if NETWORKS[network.name]['is_free']:
            return 0
        return CONTRACT_PRICE_EOS['EOS_TOKEN_STANDALONE'] * NET_DECIMALS['EOS']

    def compile(self):
        if self.temp_directory:
            print('already compiled')
            return
        dest, config = create_directory(self, sour_path='lastwill/eosiotokenstandalone/*', config_name='config.h')
        with open(config, 'w') as f:
            f.write('''#define ADMIN {admin}'''.format(admin=self.admin_address))
        if os.system("/bin/bash -c 'cd {dest} && make'".format(dest=dest)):
            raise Exception('compiler error')
        with open(path.join(dest, 'eosio.token/eosio.token.abi'), 'r') as f:
            abi = f.read()
        with open(path.join(dest, 'eosio.token/eosio.token.wasm'), 'rb') as f:
            bytecode = binascii.hexlify(f.read()).decode("utf-8")
        with open(path.join(dest, 'eosio.token.cpp'), 'rb') as f:
            source_code = f.read().decode('utf-8-sig')
        data = {
            "maximum_supply": int(self.maximum_supply / 10 ** self.decimals),
            "decimals": self.decimals,
            "symbol": self.token_short_name
        }
        print('data', data, flush=True)
        with open(path.join(dest, 'deploy_data.json'), 'w') as outfile:
            json.dump(data, outfile)
        with open(path.join(EOS_TEST_FOLDER, 'deploy_data.json'), 'w') as outfile:
            json.dump(data, outfile)
        with open((path.join(EOS_TEST_FOLDER, 'config.h')), 'w') as f:
            f.write('''#define ADMIN {admin}'''.format(admin=self.admin_address))
        if os.system("/bin/bash -c 'cd {dest} && make'".format(dest=EOS_TEST_FOLDER)):
            raise Exception('make in test folder error')
        if os.system(
                "/bin/bash -c 'cd {dest} && {env} {command}'".format(
                    dest=dest, env=EOS_TEST_URL_ENV, command=EOS_TEST_URL)

        ):
            raise Exception('compiler error token standalone')
        eos_contract = EOSContract()
        eos_contract.abi = abi
        eos_contract.bytecode = bytecode
        eos_contract.source_code = source_code
        eos_contract.contract = self.contract
        eos_contract.save()
        self.eos_contract = eos_contract
        self.save()

    @blocking
    @postponable
    def deploy(self):
        self.compile()
        wallet_name = NETWORKS[self.contract.network.name]['wallet']
        password = NETWORKS[self.contract.network.name]['eos_password']
        unlock_eos_account(wallet_name, password)
        creator_account = NETWORKS[self.contract.network.name]['address']
        our_public_key = NETWORKS[self.contract.network.name]['pub']
        if self.contract.network.name == 'EOS_MAINNET':
            eos_url = 'https://%s' % (
            str(NETWORKS[self.contract.network.name]['host']))
        else:
            eos_url = 'http://%s:%s' % (str(NETWORKS[self.contract.network.name]['host']), str(NETWORKS[self.contract.network.name]['port']))
        command = [
            'cleos', '-u', eos_url, 'system', 'newaccount',
            creator_account, self.token_account, our_public_key,
            our_public_key, '--stake-net', '5' + ' EOS',
            '--stake-cpu', '12' + ' EOS',
            '--buy-ram-kbytes', '250',
            '--transfer', '-j'
        ]
        print('command:', command, flush=True)
        tx_hash = implement_cleos_command(command)['transaction_id']
        print('tx_hash:', tx_hash, flush=True)
        self.eos_contract.tx_hash = tx_hash
        self.eos_contract.address = self.token_account
        self.eos_contract.save()
        self.contract.state = 'WAITING_FOR_DEPLOYMENT'
        self.contract.save()


    @blocking
    @postponable
    def newAccount(self, message):
        wallet_name = NETWORKS[self.contract.network.name]['wallet']
        password = NETWORKS[self.contract.network.name]['eos_password']
        creator_account = NETWORKS[self.contract.network.name]['address']
        if self.contract.network.name == 'EOS_MAINNET':
            eos_url = 'https://%s' % (
            str(NETWORKS[self.contract.network.name]['host']))
        else:
            eos_url = 'http://%s:%s' % (str(NETWORKS[self.contract.network.name]['host']), str(NETWORKS[self.contract.network.name]['port']))
        dest = path.join(CONTRACTS_TEMP_DIR, self.temp_directory)

        if self.decimals != 0:
            max_supply = str(self.maximum_supply)[:-self.decimals] + '.' + str(self.maximum_supply)[-self.decimals:]
        else:
            max_supply = str(self.maximum_supply)

        raw_data = json.dumps({'maximum_supply': max_supply + ' ' + self.token_short_name, 'issuer': self.admin_address})


        unlock_eos_account(wallet_name, password)

        contract_addr = 'eosio.token'
        command = [
                'cleos', '-u', eos_url, 'convert', 'pack_action_data', contract_addr, 'create', str(raw_data)
        ]
        print('command', command, flush=True)
        data = implement_cleos_command(command)
        print('data:', data, data[-1] == '\n')
        data = data[:-1]

        command = [
            'cleos', '-u', eos_url, 'set', 'abi', self.token_account,
            path.join(dest, 'eosio.token/eosio.token.abi'), '-jd', '-s'
        ]

        print('command:', command, flush=True)
        abi = implement_cleos_command(command)['actions'][0]['data'][20:]

        actions = create_eos_token_sa_json(
                self.token_account,
                self.eos_contract.bytecode,
                abi,
                self.admin_address,
                data
        )
        with open(path.join(dest, 'deploy_params.json'), 'w') as f:
            f.write(json.dumps(actions))
        command = [
            'cleos', '-u', eos_url, 'push', 'transaction',
            path.join(dest, 'deploy_params.json'), '-j',
            '-p', self.token_account
        ]
        print('command:', command, flush=True)
        tx_hash = implement_cleos_command(command)['transaction_id']
        print(tx_hash, flush=True)
        print('SUCCESS')
        self.eos_contract.tx_hash = tx_hash
        self.eos_contract.save()



    def deployed(self, message):
        return

    def setcode(self, message):
        return

    def msg_deployed(self, message):
        return

    def tokenCreated(self, message):
        self.contract.state = 'ACTIVE'
        self.contract.save()
        if self.contract.user.email:
            network_name = MAIL_NETWORK[self.contract.network.name]
            send_mail(
                eos_contract_subject,
                eos_contract_message.format(
                    token_name=self.token_short_name,
                    network_name=network_name
                ),
                DEFAULT_FROM_EMAIL,
                [self.contract.user.email]
            )
        take_off_blocking(self.contract.network.name, self.contract.id)
