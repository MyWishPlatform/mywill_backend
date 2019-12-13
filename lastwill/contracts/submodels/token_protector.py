from lastwill.contracts.submodels.common import *
from django.utils import timezone
from rest_framework.exceptions import ValidationError


@contract_details('Token protrctor contract')
class ContractDetailsTokenProtector():
    # test fields
    sol_path = 'lastwill/lost-key/'
    source_filename = 'contracts/LostKeyDelayedPaymentWallet.sol'
    result_filename = 'build/contracts/LostKeyDelayedPaymentWallet.json'
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

    def get_arguments(self, *args, **kwargs):
        pass

    def fundsAdded(self, message):
        pass

    @classmethod
    def min_cost(cls):
        pass

    @staticmethod
    def calc_cost(kwargs, network):
        pass

    @postponable
    @check_transaction
    def msg_deployed(self, message):
        pass

    @check_transaction
    def checked(self, message):
        pass

    @check_transaction
    def triggered(self, message):
        pass

    def get_gaslimit(self):
        pass

    @blocking
    @postponable
    def deploy(self):
        pass


    def contractPayment(self, message):
        pass

    @blocking
    def make_payment(self, message):
        pass

    @blocking
    def cancel(self, message):
        pass

    def compile(self, eth_contract_attr_name='eth_contract_token'):
        pass


    def finalized(self, message):
        pass
