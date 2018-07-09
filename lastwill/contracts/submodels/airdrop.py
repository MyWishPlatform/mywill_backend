from django.db import models

from lastwill.contracts.submodels.common import *


class AirdropAddress(models.Model):
    contract = models.ForeignKey(Contract, null=True)
    address = models.CharField(max_length=50, db_index=True)
    active = models.BooleanField(default=True)
    state = models.CharField(max_length=10, default='added')
    amount = models.DecimalField(
        max_digits=MAX_WEI_DIGITS, decimal_places=0, null=True,
        db_index=True
    )


@contract_details('Airdrop')
class ContractDetailsAirdrop(CommonDetails):

    contract = models.ForeignKey(Contract, null=True)
    admin_address = models.CharField(max_length=50)
    token_address = models.CharField(max_length=50)
    eth_contract = models.ForeignKey(EthContract, null=True, default=None)

    @logging
    def get_arguments(self, *args, **kwargs):
        return [
            self.admin_address,
            self.token_address
        ]

    def compile(self, _=''):
        dest = path.join(CONTRACTS_DIR, 'lastwill/airdrop-contract/')
        with open(path.join(dest, 'build/contracts/AirDrop.json'), 'rb') as f:
            airdrop_json = json.loads(f.read().decode('utf-8-sig'))
        with open(path.join(dest, 'build/contracts/AirDrop.sol'), 'rb') as f:
            source_code = f.read().decode('utf-8-sig')
        self.eth_contract = create_ethcontract_in_compile(
            airdrop_json['abi'], airdrop_json['bytecode'][2:],
            airdrop_json['compiler']['version'], self.contract, source_code
        )
        self.save()

    @blocking
    @postponable
    @logging
    def deploy(self):
        return super().deploy()

    @staticmethod
    def calc_cost(kwargs, network):
        if NETWORKS[network.name]['is_free']:
            return 0
        return 2 * 10**18

    @classmethod
    def min_cost(cls):
        network = Network.objects.get(name='ETHEREUM_MAINNET')
        cost = cls.calc_cost({}, network)
        return cost

    def get_gaslimit(self):
        return 3000000
