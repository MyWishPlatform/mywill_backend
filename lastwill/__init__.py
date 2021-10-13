# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
from subprocess import Popen, PIPE
from .celery import app as celery_app
from .settings import BASE_DIR, SOLANA_CLI_DIR, NETWORKS

__all__ = ('celery_app',)

# Setup Solana cli
setup_keypair = Popen([f'./solana config set --keypair {BASE_DIR}/keypair.json'],
                      stdin=PIPE, stdout=PIPE, stderr=PIPE, cwd=SOLANA_CLI_DIR, shell=True)

setup_network = Popen([f'./solana config set --url {NETWORKS["SOLANA_TESTNET"]["node_url"]}'],
                      stdin=PIPE, stdout=PIPE, stderr=PIPE, cwd=SOLANA_CLI_DIR, shell=True)

def setup():
    for process in [setup_keypair, setup_network]:
        stdout, stderr = process.communicate()
        print(stdout.decode(), stderr.decode(), flush=True)
        if process.returncode != 0:
            raise Exception('encountered an error while setting up solana ')
        print('successfully set up Solana cli ')
    return True

setup()
