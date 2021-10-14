from subprocess import Popen, PIPE
from lastwill.settings import SOLANA_CLI_DIR, DEFAULT_FROM_EMAIL
from lastwill.consts import NET_DECIMALS, CONTRACT_PRICE_USDT, VERIFICATION_PRICE_USDT, WHITELABEL_PRICE_USDT
from lastwill.contracts.submodels.common import *
from email_messages import solana_token_text


class SolanaContract(EthContract):
    pass


@contract_details('Solana SPL Token contract')
class ContractDetailsSolanaToken(CommonDetails):
    solana_contract = models.ForeignKey(SolanaContract, null=True, default=None)
    token_name = models.CharField(max_length=50)
    token_short_name = models.CharField(max_length=10)
    decimals = models.IntegerField()
    admin_address = models.CharField(max_length=70)
    future_minting = models.BooleanField(default=False)
    token_type = models.CharField(max_length=32, default='SPL')
    transfer_tx_hash = models.CharField(max_length=90, null=True, default=None)

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
    @check_transaction
    def deploy(self):
        print('deploying solana SPL token')
        process = Popen(['./spl-token create-token'], stdin=PIPE, stdout=PIPE, stderr=PIPE, cwd=SOLANA_CLI_DIR,
                        shell=True)

        stdout, stderr = process.communicate()

        print(stdout.decode(), stderr.decode(), flush=True)

        if process.returncode != 0:
            raise Exception('error while deploying')

        success_result = stdout.decode()
        print(success_result)
        tx_hash = success_result.split("Signature: ", 1)[1][:-2]
        contract_address = success_result.split("Signature: ", 1)[0].split('Creating token ')[1][:-2]

        solana_contract = SolanaContract()
        solana_contract.contract = self.contract
        solana_contract.original_contract = self.contract
        solana_contract.tx_hash = tx_hash
        solana_contract.address = contract_address
        solana_contract.save()
        self.solana_contract = solana_contract
        self.save()
        self.msg_deployed({})

    @blocking
    @postponable
    @check_transaction
    def msg_deployed(self, message):
        print('msg_deployed method of the solana token contract')
        if self.contract.state != 'WAITING_FOR_DEPLOYMENT':
            take_off_blocking(self.contract.network.name)
            return
        else:
            print('transferring of ownership started')
            owner = self.admin_address
            address = self.solana_contract.address
            process = Popen([f'./spl-token authorize {address} owner {owner}'], stdin=PIPE, stdout=PIPE, stderr=PIPE,
                            cwd=SOLANA_CLI_DIR,
                            shell=True)

            stdout, stderr = process.communicate()

            print(stdout.decode(), stderr.decode(), flush=True)

            if process.returncode != 0:
                raise Exception('error while transferring owner')

            success_result = stdout.decode()
            print(success_result)
            tx_hash = success_result.split("Signature: ", 1)[1][:-2]
            self.transfer_tx_hash = tx_hash
            self.save()
            print('transferOwnership success')
            self.initialized()

    @postponable
    @check_transaction
    def initialized(self, message):
        if self.contract.state not in ('WAITING_FOR_DEPLOYMENT', 'ENDED'):
            return

        take_off_blocking(self.contract.network.name)

        self.contract.state = 'ACTIVE' if self.future_minting else 'ENDED'
        self.contract.deployed_at = datetime.datetime.now()
        self.contract.save()
        if self.contract.user.email:
            send_mail(
                common_subject,
                solana_token_text.format(addr=self.solana_contract.address),
                DEFAULT_FROM_EMAIL,
                [self.contract.user.email]
            )
            if not 'MAINNET' in self.contract.network.name:
                send_testnet_gift_emails.delay(self.contract.user.profile.id)
            else:
                send_promo_mainnet.delay(self.contract.user.email)

        msg = self.bot_message
        transaction.on_commit(lambda: send_message_to_subs.delay(msg, True))

    def finalized(self, message):
        pass
