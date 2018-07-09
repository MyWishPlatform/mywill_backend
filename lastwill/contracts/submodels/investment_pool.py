from django.db import models

from lastwill.contracts.submodels.common import *


@contract_details('Investment Pool')
class ContractDetailsInvestmentPool(CommonDetails):

    contract = models.ForeignKey(Contract, null=True)
    admin_address = models.CharField(max_length=50)
    admin_percent = models.FloatField()
    ico_address = models.CharField(max_length=50)
    temp_directory = models.CharField(max_length=36)
    eth_contract = models.ForeignKey(EthContract, null=True, default=None)
    start_date = models.IntegerField()
    stop_date = models.IntegerField()
    decimals = models.IntegerField()
    whitelist = models.BooleanField(default=False)
    investment = models.BooleanField(default=False)
    investment_address = models.CharField(max_length=50, default='')
    allow_change_dates = models.BooleanField(default=False)
    send_tokens_hard_cap = models.BooleanField(default=False)
    send_tokens_soft_cap = models.BooleanField(default=False)

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
            self.ico_address
        ]

    def compile(self, _=''):
        self.lgr.append('compile %d' % self.contract.id)
        print('investment pool contract compile')
        if self.temp_directory:
            print('already compiled')
            self.lgr.append('already compiled')
            return
        dest, preproc_config = create_directory(self, sour_path='lastwill/investment_pool')
        self.lgr.append('dest %s' % dest)
        preproc_params = {'constants': {}}

        preproc_params["D_SOFT_CAP_WEI"] = str(self.soft_cap)
        preproc_params["D_HARD_CAP_WEI"] = str(self.hard_cap)

        if self.min_wei:
            preproc_params["constants"]["D_MIN_VALUE_WEI"] = str(
                int(self.min_wei))
        if self.max_wei:
            preproc_params["constants"]["D_MAX_VALUE_WEI"] = str(
                int(self.max_wei))

        test_investment_pool_params(preproc_config, preproc_params, dest)
        address = NETWORKS[self.contract.network.name]['address']
        # preproc_params = add_real_params(
        #     preproc_params, self.admin_address,
        #     address, self.cold_wallet_address
        # )
        # self.lgr.append(('prepoc params', preproc_params))
        # with open(preproc_config, 'w') as f:
        #     f.write(json.dumps(preproc_params))
        # if os.system(
        #         "/bin/bash -c 'cd {dest} && yarn compile-crowdsale'".format(
        #             dest=dest)
        # ):
        #     raise Exception('compiler error while deploying')
        # with open(path.join(dest, 'build/contracts/TemplateCrowdsale.json'),
        #           'rb') as f:
        #     crowdsale_json = json.loads(f.read().decode('utf-8-sig'))
        # with open(path.join(dest, 'build/TemplateCrowdsale.sol'), 'rb') as f:
        #     source_code = f.read().decode('utf-8-sig')
        # self.eth_contract = create_ethcontract_in_compile(
        #     crowdsale_json['abi'], crowdsale_json['bytecode'][2:],
        #     crowdsale_json['compiler']['version'], self.contract, source_code
        # self.save()
        return super().deploy()

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
