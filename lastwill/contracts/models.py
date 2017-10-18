from subprocess import Popen, PIPE
from os import path
import requests
import json
import binascii
import datetime
from ethereum import abi
from django.db import models
from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField
from django.utils import timezone
from lastwill.settings import ORACLIZE_PROXY, SIGNER
from lastwill.parint import *
from lastwill.contracts.types import contract_types


MAX_WEI_DIGITS = len(str(2**256))

class Contract(models.Model):
    name = models.CharField(max_length=200, null=True, default=None)
    user = models.ForeignKey(User)
    address = models.CharField(max_length=50, null=True, default=None)
    owner_address = models.CharField(max_length=50, null=True, default=None)
    user_address = models.CharField(max_length=50, null=True, default=None)
    state = models.CharField(max_length=63, default='CREATED')
    created_date = models.DateTimeField(auto_now=True)
    source_code = models.TextField()
    bytecode = models.TextField()
    abi = JSONField(default={})
    compiler_version = models.CharField(max_length=200, null=True, default=None)
    check_interval = models.IntegerField()
    active_to = models.DateTimeField()
    balance = models.DecimalField(max_digits=MAX_WEI_DIGITS, decimal_places=0, null=True, default=None)
    cost = models.DecimalField(max_digits=MAX_WEI_DIGITS, decimal_places=0)
    last_check = models.DateTimeField(null=True, default=None)
    next_check = models.DateTimeField(null=True, default=None)
    contract_type = models.IntegerField(default=0)

    @staticmethod
    def calc_cost(heirs_num, active_to, check_interval):
        Tg = 22000
        Gp = 20 * 10 ** 9
        Cg = 780476
        CBg = 26561
        Dg = 29435
        DBg = 9646
        B = heirs_num
        Cc = 124852
        DxC = max(abs((datetime.date.today() - active_to).total_seconds() / check_interval), 1)
        O = 25000 * 10 ** 9
        return 2 * int(Tg * Gp + Gp * (Cg + B * CBg) + Gp * (Dg + DBg * B) + (Gp * Cc + O) * DxC)

    def compile(self):
        sol_path = contract_types[self.contract_type]['sol_path']
        with open(sol_path) as f:
            source = f.read()
        directory = path.dirname(sol_path)
        result = json.loads(Popen(
                'solc --optimize --combined-json abi,bin --allow-paths={}'.format(directory).split(),
                stdin=PIPE,
                stdout=PIPE,
                cwd=directory
        ).communicate(source.encode())[0].decode())
        self.source_code = source
        self.compiler_version = result['version']
        sol_path_name = os.path.basename(sol_path)[:4]
        self.abi = json.loads(result['contracts']['<stdin>:'+sol_path_name]['abi'])
        self.bytecode = result['contracts']['<stdin>:'+sol_path_name]['bin']

    def deploy(self):
        self.compile()
        tr = abi.ContractTranslator(self.abi)
        arguments = contract_types[self.contract_type]['get_arguments']()
        par_int = ParInt()
        nonce = int(par_int.parity_nextNonce(self.owner_address), 16)
        print('nonce', nonce)

        signed_data = json.loads(requests.post('http://{}/sign/'.format(SIGNER), json={
                'source' : self.owner_address,
                'data': self.bytecode + binascii.hexlify(tr.encode_constructor_arguments(arguments)).decode(),
                'nonce': nonce
        }).content.decode())['result']
        print('signed_data', signed_data)

        par_int.eth_sendRawTransaction('0x' + signed_data)

        self.state = 'WAITING_FOR_DEPLOYMENT'

        self.save()

    def save(self, *args, **kwargs):
        # disable balance saving to prevent collisions with java daemon
        print(args)
        if self.id:
            kwargs['update_fields'] = list(
                    {f.name for f in Contract._meta.fields if f.name not in ('balance', 'id')}
                    &
                    set(kwargs.get('update_fields', [f.name for f in Contract._meta.fields]))
            )
        return super().save(*args, **kwargs)
        
class Heir(models.Model):
    contract = models.ForeignKey(Contract)
    address = models.CharField(max_length=50)
    percentage = models.IntegerField()
    email = models.CharField(max_length=200, null=True)
