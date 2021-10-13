from subprocess import Popen, PIPE
from lastwill.settings import NETWORKS, SOLANA_CLI_DIR, BASE_DIR

setup_keypair = Popen([f'./solana config set --keypair {BASE_DIR}/keypair.json'],
                      stdin=PIPE, stdout=PIPE, stderr=PIPE, cwd=SOLANA_CLI_DIR, shell=True)

setup_network = Popen([f'./solana config set --url {NETWORKS["SOLANA_TESTNET"]["node_url"]}'],
                      stdin=PIPE, stdout=PIPE, stderr=PIPE, cwd=SOLANA_CLI_DIR, shell=True)

for process in [setup_keypair, setup_network]:
    stdout, stderr = process.communicate()
    print(stdout.decode(), stderr.decode(), flush=True)
    if process.returncode != 0:
        raise Exception('encountered an error while setting up solana ')
