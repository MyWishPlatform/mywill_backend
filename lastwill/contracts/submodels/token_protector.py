from lastwill.contracts.submodels.common import *
from django.utils import timezone
from rest_framework.exceptions import ValidationError
import datetime
from lastwill.consts import NET_DECIMALS, CONTRACT_GAS_LIMIT


@contract_details('Token protrctor contract')
class ContractDetailsTokenProtector(CommonDetails):
    # test fields
    sol_path = 'lastwill/token-protector/'
    source_filename = 'contracts/TokenProtector.sol'
    result_filename = 'build/contracts/TokenProtector.json'
    user_address = models.CharField(max_length=50, null=True, default=None)

    check_interval = models.IntegerField()
    active_to = models.DateTimeField()

    last_check = models.DateTimeField(null=True, default=None)
    next_check = models.DateTimeField(null=True, default=None)

    eth_contract = models.ForeignKey(EthContract, null=True, default=None)

    transfer_threshold_wei = models.IntegerField(default=0)
    transfer_delay_seconds = models.IntegerField(default=0)

    def predeploy_validate(self):
        now = timezone.now()
        if self.active_to < now:
            raise ValidationError({'result': 1}, code=400)

    @postponable
    @check_transaction
    def msg_deployed(self, message):
        super().msg_deployed(message)
        self.next_check = timezone.now() + datetime.timedelta(seconds=self.check_interval)
        self.save()

    @classmethod
    def min_cost(cls):
        network = Network.objects.get(name='ETHEREUM_MAINNET')
        cost = cls.calc_cost({}, network)
        return cost

    @staticmethod
    def calc_cost(kwargs, network):
        if NETWORKS[network.name]['is_free']:
            return 0
        return int(25 * NET_DECIMALS['USDT'])


    def get_gaslimit(self):
        return CONTRACT_GAS_LIMIT['TOKEN_PROTECTOR']

    @blocking
    @postponable
    def deploy(self):
        super().deploy()


    def compile(self, eth_contract_attr_name='eth_contract_token'):
        pass

    @check_transaction
    def checked(self, message):
        now = timezone.now()
        self.last_check = now
        next_check = now + datetime.timedelta(seconds=self.check_interval)
        if next_check < self.active_to:
            self.next_check = next_check
        else:
            self.contract.state = 'EXPIRED'
            self.contract.save()
            self.next_check = None
        self.save()
        take_off_blocking(self.contract.network.name, self.contract.id)

    @check_transaction
    def triggered(self, message):
        link = NETWORKS[self.eth_contract.contract.network.name]['link_tx']
        if self.recepient_email:
            send_mail(
                heir_subject,
                heir_message.format(
                    user_address=self.recepient_address,
                    link_tx=link.format(tx=message['transactionHash'])
                ),
                DEFAULT_FROM_EMAIL,
                [self.recepient_email]
            )
        self.contract.state = 'TRIGGERED'
        self.contract.save()
        if self.contract.user.email:
            send_mail(
                carry_out_subject,
                carry_out_message,
                DEFAULT_FROM_EMAIL,
                [self.contract.user.email]
            )

    def get_arguments(self, *args, **kwargs):
        return [
            self.user_address,
            # self.recepient_address,
            2 ** 256 - 1,
            int(self.date.timestamp()),
        ]

    # def contractPayment(self, message):
    #     pass
    #
    # @blocking
    # def make_payment(self, message):
    #     pass


    # @blocking
    # def i_am_alive(self, message):
    #     pass
    #
    # @blocking
    # def cancel(self, message):
    #     pass
    #
    # def fundsAdded(self, message):
    #     pass
