from django.db import models

from lastwill.contracts.submodels.common import *


class InvestAddress(models.Model):
    contract = models.ForeignKey(Contract, null=True)
    address = models.CharField(max_length=50, db_index=True)
    take_away = models.BooleanField(default=False)
    created_date = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(
        max_digits=MAX_WEI_DIGITS, decimal_places=0, null=True,
        db_index=True
    )


@contract_details('Investment Pool')
class ContractDetailsInvestmentPool(CommonDetails):

    contract = models.ForeignKey(Contract, null=True)
    admin_address = models.CharField(max_length=50)
    admin_percent = models.FloatField()
    temp_directory = models.CharField(max_length=36)
    eth_contract = models.ForeignKey(EthContract, null=True, default=None)
    start_date = models.IntegerField()
    stop_date = models.IntegerField()
    whitelist = models.BooleanField(default=False)
    investment_address = models.CharField(max_length=50, default=None, null=True)
    token_address = models.CharField(max_length=50, default=None, null=True)
    allow_change_dates = models.BooleanField(default=False)
    send_tokens_hard_cap = models.BooleanField(default=False)
    send_tokens_soft_cap = models.BooleanField(default=False)
    link = models.CharField(max_length=50, unique=True)

    soft_cap = models.DecimalField(
        max_digits=MAX_WEI_DIGITS, decimal_places=0, null=True
    )
    hard_cap = models.DecimalField(
        max_digits=MAX_WEI_DIGITS, decimal_places=0, null=True
    )
    min_wei = models.DecimalField(
        max_digits=MAX_WEI_DIGITS, decimal_places=0, default=None, null=True
    )
    max_wei = models.DecimalField(
        max_digits=MAX_WEI_DIGITS, decimal_places=0, default=None, null=True
    )

    @logging
    def get_arguments(self, *args, **kwargs):
        return [
                self.admin_address,
                self.investment_address if self.investment_address else '0x'+'0'*40,
                self.token_address if self.token_address else '0x'+'0'*40
        ]

    def compile(self, _=''):
        self.lgr.append('compile %d' % self.contract.id)
        print('investment pool contract compile')
        if self.temp_directory:
            print('already compiled')
            self.lgr.append('already compiled')
            return
        dest, preproc_config = create_directory(
            self, sour_path='lastwill/investment-pool/*',
            config_name='investment-pool-config.json'
        )
        self.lgr.append('dest %s' % dest)
        preproc_params = {'constants': {}}

        preproc_params["constants"]["D_SOFT_CAP_WEI"] = str(self.soft_cap)
        preproc_params["constants"]["D_HARD_CAP_WEI"] = str(self.hard_cap)
        preproc_params["constants"]["D_START_TIME"] = self.start_date
        preproc_params["constants"]["D_END_TIME"] = self.stop_date
        preproc_params["constants"]["D_WHITELIST"] = "true" if self.whitelist else "false"
        preproc_params["constants"]["D_CAN_CHANGE_TIMES"] = "true" if self.allow_change_dates else "false"
        preproc_params["constants"]["D_CAN_FINALIZE_AFTER_HARD_CAP_ONLY_OWNER"] = "true" if self.send_tokens_hard_cap else "false"
        preproc_params["constants"]["D_CAN_FINALIZE_AFTER_SOFT_CAP_ONLY_OWNER"] = "true" if self.send_tokens_soft_cap else "false"
        preproc_params["constants"]["D_MIN_VALUE_WEI"] = "0"
        preproc_params["constants"]["D_MAX_VALUE_WEI"] = "0"
        preproc_params["constants"]["D_REWARD_PERMILLE"] = int(self.admin_percent * 10)

        if self.min_wei:
            preproc_params["constants"]["D_MIN_VALUE_WEI"] = str(
                int(self.min_wei))
        if self.max_wei:
            preproc_params["constants"]["D_MAX_VALUE_WEI"] = str(
                int(self.max_wei))

        test_investment_pool_params(preproc_config, preproc_params, dest)
        with open(preproc_config, 'w') as f:
            f.write(json.dumps(preproc_params))
        with open(path.join(dest, 'build/contracts/InvestmentPool.json'),
                  'rb') as f:
            investment_json = json.loads(f.read().decode('utf-8-sig'))
        with open(path.join(dest, 'build/InvestmentPool.sol'), 'rb') as f:
            source_code = f.read().decode('utf-8-sig')
        self.eth_contract = create_ethcontract_in_compile(
            investment_json['abi'], investment_json['bytecode'][2:],
            investment_json['compiler']['version'], self.contract, source_code
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
