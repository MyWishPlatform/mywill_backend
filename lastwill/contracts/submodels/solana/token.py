from spl.token.client import Token
from spl.token.constants import TOKEN_PROGRAM_ID
from spl.token.instructions import get_associated_token_address
from solana.rpc.core import RPCException
from solana.keypair import Keypair
from solana.publickey import PublicKey
from lastwill.settings import DEFAULT_FROM_EMAIL, SOLANA_KEYPAIR
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
    def deploy(self):
        print('deploying solana SPL token')
        conn = SolanaInt(self.contract.network.name).connect()
        owner = PublicKey(str(self.admin_address))
        key = Keypair.from_secret_key(bytes(SOLANA_KEYPAIR[0:32]))
        balance_needed = Token.get_min_balance_rent_for_exempt_for_mint(conn)
        token, txn, payer, mint_account, opts = Token._create_mint_args(conn, key, key.public_key, self.decimals,
                                                                        TOKEN_PROGRAM_ID,
                                                                        owner, False, balance_needed, Token)

        response = conn.send_transaction(txn, payer, mint_account, opts=opts)
        print(response)
        error = response['result']['meta']['err']
        if error:
            raise Exception(f'error while deploying \n {error}')
        else:
            tx_hash = response['result']['transaction']['signatures'][0]
            contract_address = response['result']['transaction']['message']['accountKeys'][1]
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
        print('msg_deployed method of the solana spl token')
        if self.contract.state != 'WAITING_FOR_DEPLOYMENT':
            take_off_blocking(self.contract.network.name)
            return
        else:
            conn = SolanaInt(self.contract.network.name).connect()
            key = Keypair.from_secret_key(bytes(SOLANA_KEYPAIR[0:32]))
            tok = Token(conn, self.solana_contract.address, TOKEN_PROGRAM_ID, key)
            holders = self.contract.tokenholder_set.all()
            if holders:
                print('transfering premint tokens')
                for th in holders:
                    holder_addr = PublicKey(th.address)
                    try:
                        associated_address = tok.create_associated_token_account(holder_addr)
                        print(f'created associated account {associated_address}')
                    except RPCException:
                        print('associated token account already created')
                        associated_address = get_associated_token_address(holder_addr, tok.pubkey)
                    response = tok.mint_to(associated_address, key, th.amount)
                    print(f'tx_hash = {response["result"]}')

            print('transferring of mint authority started')
            owner = PublicKey(self.admin_address)
            address = self.solana_contract.address
            tok.set_authority(address, key.public_key, 0, owner)
            print('successfully transferred mint authority')

            self.initialized()

    @postponable
    @check_transaction
    def initialized(self, message):
        if self.contract.state not in ('WAITING_FOR_DEPLOYMENT', 'ENDED'):
            take_off_blocking(self.contract.network.name)
            return

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
