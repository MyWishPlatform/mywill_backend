import sys
import os
from pathlib import Path

sys.path.append(Path(__file__).resolve().parents[1].resolve().as_posix())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lastwill.settings')
import django

django.setup()

from hdwallet import BIP44HDWallet
from hdwallet.cryptocurrencies import EthereumMainnet
from hdwallet.derivations import BIP44Derivation
from hdwallet.utils import generate_mnemonic
from typing import Optional

from lastwill.contracts.submodels.common import CommonDetails
from settings_local import ROOT_EXT_KEY

import json
import pathlib

wallet_file = pathlib.Path("wallwt_data.json")

if wallet_file.exists():
    with open(str(wallet_file), "r") as wallet_f:
        wallet_data = json.loads(wallet_f.read())

elif True:
    white_labels = CommonDetails.objects.filter(white_label=True)

    # Generate english mnemonic words

    MNEMONIC: str = generate_mnemonic(language="english", strength=128)
    # Secret passphrase/password for mnemonic
    PASSPHRASE: Optional[str] = None  # "meherett"

    # Initialize Ethereum mainnet BIP44HDWallet
    bip44_hdwallet: BIP44HDWallet = BIP44HDWallet(cryptocurrency=EthereumMainnet)
    # Get Ethereum BIP44HDWallet from mnemonic
    bip44_hdwallet.from_xprivate_key(
        xprivate_key=ROOT_EXT_KEY
    )
    # Clean default BIP44 derivation indexes/paths
    bip44_hdwallet.clean_derivation()

    print("Mnemonic:", bip44_hdwallet.mnemonic())
    print("Base HD Path:  m/44'/60'/0'/0/{address_index}", "\n")

    data = []

    # Get Ethereum BIP44HDWallet information's from address index
    for white_label in white_labels:
        address_index = white_label.contract.address
        # Derivation from Ethereum BIP44 derivation path
        bip44_derivation: BIP44Derivation = BIP44Derivation(
            cryptocurrency=EthereumMainnet, account=0, change=False, address=address_index
        )
        # Drive Ethereum BIP44HDWallet
        bip44_hdwallet.from_path(path=bip44_derivation)
        # Print address_index, path, address and private_key
        print(f"({address_index}) {bip44_hdwallet.path()} {bip44_hdwallet.address()} 0x{bip44_hdwallet.private_key()}")

        data.append({"path": bip44_hdwallet.path(),
                     "address": bip44_hdwallet.address(),
                     "key": f"0x{bip44_hdwallet.private_key()}"})
        # Clean derivation indexes/paths
        bip44_hdwallet.clean_derivation()

    data_json = json.dumps(data)
    with open(str(wallet_file), "w+") as wallet_f:
        wallet_f.write(data_json)


