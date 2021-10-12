import base58
from lastwill.contracts.submodels.common import *
from lastwill.consts import NET_DECIMALS, CONTRACT_PRICE_USDT, VERIFICATION_PRICE_USDT, WHITELABEL_PRICE_USDT
from subprocess import Popen, PIPE


class SolanaContract(EthContract):
    pass


def solana_address_to_hex(address):
    bytes = solana_address_to_bytes(address)
    bytes = bytearray(bytes)
    bytes.reverse()
    return '0x' + bytes.hex()


def solana_address_to_bytes(address):
    return base58.b58decode_check(address)[1:]


@contract_details('Solana SPL Token contract')
class ContractDetailsSolanaToken(CommonDetails):
    solana_contract = models.ForeignKey(SolanaContract, null=True, default=None)
    token_name = models.CharField(max_length=50)
    token_short_name = models.CharField(max_length=10)
    decimals = models.IntegerField()
    admin_address = models.CharField(max_length=70)
    future_minting = models.BooleanField(default=False)
    token_type = models.CharField(max_length=32, default='SPL')


    @classmethod
    def min_cost(cls):
        network = Network.objects.get(name='SOLANA_TESTNET')
        cost = cls.calc_cost({}, network)
        return cost

    @staticmethod
    def calc_cost(kwargs, network):
        if NETWORKS[network.name]['is_free']:
            return 0
        price = CONTRACT_PRICE_USDT['SOLANA_TOKEN']
        if 'verification' in kwargs and kwargs['verification']:
            price += VERIFICATION_PRICE_USDT
        if 'white_label' in kwargs and kwargs['white_label']:
            price += WHITELABEL_PRICE_USDT
        return price * NET_DECIMALS['USDT']

    @blocking
    @postponable
    def deploy(self):
        pass
        # process = Popen(['./'], stdin=PIPE, stdout=PIPE, stderr=PIPE, cwd=solana, shell=True)
        #
        #
        # stdout, stderr = process.communicate()
        #
        # print(stdout.decode(), stderr.decode(), flush=True)
        # if process.returncode != 0:
        #     raise Exception('error while deploying')
        #
        # data = stdout.decode()
        # print(data)
        # tx_hash = data.split("Signed and relayed transaction with hash ", 1)[1][:66]
        # contract_address = data.split("Contract hash: ", 1)[1].split('\n')[0][:42]
        #
        # solana_contract = SolanaContract()
        # solana_contract.contract = self.contract
        # solana_contract.original_contract = self.contract
        # solana_contract.tx_hash = tx_hash
        # solana_contract.address = contract_address
        # solana_contract.save()
        # self.solana_contract = solana_contract
        # self.save()
        # self.initialized({})

    @blocking
    @postponable
    @check_transaction
    def msg_deployed(self, message):
        pass

    @postponable
    @check_transaction
    def initialized(self, message):
        if self.contract.state  not in ('WAITING_FOR_DEPLOYMENT', 'ENDED'):
            return

        take_off_blocking(self.contract.network.name)

        self.contract.state = 'ACTIVE' if self.future_minting else 'ENDED'
        self.contract.deployed_at = datetime.datetime.now()
        self.contract.save()
        if self.contract.user.email:
            send_mail()
            if not 'MAINNET' in self.contract.network.name:
                send_testnet_gift_emails.delay(self.contract.user.profile.id)
            else:
                send_promo_mainnet.delay(self.contract.user.email)


        msg = self.bot_message
        transaction.on_commit(lambda: send_message_to_subs.delay(msg, True))

    def finalized(self, message):
        self.contract.state = 'ENDED'
        self.contract.save()
