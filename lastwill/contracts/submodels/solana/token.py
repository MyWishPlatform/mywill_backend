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
from time import sleep


def confirm_solana_tx(response, network):
    conn = SolanaInt(network.name).connect()
    for attempt in range(5):
        print(f'attempt {attempt} to confirm transaction', flush=True)
        tx_data = conn.get_transaction(response['result'])
        if tx_data['result'] is not None:
            print(tx_data)
            error = tx_data['result']['meta']['err']
            if error:
                raise Exception(f'transaction reverted \n {error}')
            return tx_data
        else:
            sleep(60)

    raise Exception('unable to confirm transaction')


class SolanaContract(EthContract):
    pass


class SolanaTokenLogo(models.Model):
    # logo = models.ImageField(upload_to=get_path)
    logo = models.ImageField(upload_to='')
    user_id = models.ForeignKey(User, null=True, default=None, on_delete=models.CASCADE)


class SolanaTokenInfo(models.Model):
    contract_id = models.ForeignKey(Contract, null=True, default=None, unique=True, on_delete=models.CASCADE)
    logo = models.ForeignKey(SolanaTokenLogo, null=True, default=None, on_delete=models.CASCADE)
    site_link = models.CharField(max_length=40, null=True, default=None)
    coingecko_id = models.CharField(max_length=40, null=True, default=None)
    description = models.CharField(max_length=40, null=True, default=None)
    disc_link = models.CharField(max_length=40, null=True, default=None)
    twitter_link = models.CharField(max_length=40, null=True, default=None)


@contract_details('Solana SPL Token contract')
class ContractDetailsSolanaToken(CommonDetails):
    solana_contract = models.ForeignKey(SolanaContract, null=True, default=None, on_delete=models.CASCADE)
    token_info = models.ForeignKey(SolanaTokenInfo, null=True, default=None, on_delete=models.CASCADE)
    token_name = models.CharField(max_length=50)
    token_short_name = models.CharField(max_length=10)
    decimals = models.IntegerField()
    admin_address = models.CharField(max_length=70)
    future_minting = models.BooleanField(default=False)
    token_type = models.CharField(max_length=32, default='SPL')
    transfer_tx_hash = models.CharField(max_length=90, null=True, default=None)

    @classmethod
    def min_cost(cls):
        network = Network.objects.get(name='SOLANA_MAINNET')
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
                                                                        owner, True, balance_needed, Token)

        response = conn.send_transaction(txn, payer, mint_account, opts=opts)
        print(f'tx hash = ', response["result"])
        tx_data = confirm_solana_tx(response, self.contract.network)

        tx_hash = tx_data['result']['transaction']['signatures'][0]
        contract_address = tx_data['result']['transaction']['message']['accountKeys'][1]
        solana_contract = SolanaContract()
        solana_contract.contract = self.contract
        solana_contract.original_contract = self.contract
        solana_contract.tx_hash = tx_hash
        solana_contract.address = contract_address
        solana_contract.save()
        self.solana_contract = solana_contract
        self.save()
        self.msg_deployed({})

    def msg_deployed(self, message):
        print('msg_deployed method of the solana spl token')
        if self.contract.state != 'WAITING_FOR_DEPLOYMENT':
            take_off_blocking(self.contract.network.name)
            return
        else:
            conn = SolanaInt(self.contract.network.name).connect()
            key = Keypair.from_secret_key(bytes(SOLANA_KEYPAIR[0:32]))
            token_address = PublicKey(self.solana_contract.address)
            tok_int = Token(conn, token_address, TOKEN_PROGRAM_ID, key)
            holders = self.contract.tokenholder_set.all()
            if holders:
                print('transfering premint tokens')
                for th in holders:
                    holder_addr = PublicKey(th.address)
                    try:
                        associated_address, txn, payer, opts = tok_int._create_associated_token_account_args(
                            holder_addr,
                            skip_confirmation=True)
                        response = conn.send_transaction(txn, payer, opts=opts)
                        print(f'tx hash = ', response["result"])
                        confirm_solana_tx(response, self.contract.network)
                        print(f'created associated account {associated_address}')
                    except RPCException:
                        print('associated token account already created')
                        associated_address = get_associated_token_address(holder_addr, tok_int.pubkey)
                    response = tok_int.mint_to(associated_address, key, int(th.amount))
                    print(f'tx hash = ', response['result'])
                    confirm_solana_tx(response, self.contract.network)

            print('transferring of mint authority started')
            owner = PublicKey(self.admin_address)
            address = self.solana_contract.address
            response = tok_int.set_authority(address, key.public_key, 0, owner)
            confirm_solana_tx(response, self.contract.network)
            print('successfully transferred mint authority')

            self.initialized({})

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
