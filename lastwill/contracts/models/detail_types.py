from django.apps import apps


contract_details_types = {}

lastwill = apps.get_model('contracts', 'ContractDetailsLastwill')
lostkey = apps.get_model('contracts', 'ContractDetailsLostKey')
deffered = apps.get_model('contracts', 'ContractDetailsDelayedPayment')
ico = apps.get_model('contracts', 'ContractDetailsICO')
token = apps.get_model('contracts', 'ContractDetailsToken')
neo = apps.get_model('contracts', 'ContractDetailsNeo')
neo_ico = apps.get_model('contracts', 'ContractDetailsNeoICO')
airdrop = apps.get_model('contracts', 'ContractDetailsAirdrop')


contract_details_types[0] = {'name': 'Will contract', 'model': lastwill}
contract_details_types[1] = {'name': 'Wallet contract (lost key)', 'model': lostkey}
contract_details_types[2] = {'name': 'Deferred payment contract', 'model': deffered}
contract_details_types[4] = {'name': 'MyWish ICO', 'model': ico}
contract_details_types[5] = {'name': 'Token contract', 'model': token}
contract_details_types[6] = {'name': 'NEO contract', 'model': neo}
contract_details_types[7] = {'name': 'MyWish NEO ICO', 'model': neo_ico}
contract_details_types[8] = {'name': 'Airdrop', 'model':airdrop}
