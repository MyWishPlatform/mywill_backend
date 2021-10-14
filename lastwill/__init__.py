# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
from subprocess import Popen, PIPE
from .celery import app as celery_app
from .settings import BASE_DIR, SOLANA_CLI_DIR, NETWORKS

__all__ = ('celery_app',)

# Setup Solana cli
setup_config = Popen(
    [f'./solana config set --keypair {BASE_DIR}/keypair.json --url {NETWORKS["SOLANA_TESTNET"]["node_url"]}'],
    stdin=PIPE, stdout=PIPE, stderr=PIPE, cwd=SOLANA_CLI_DIR, shell=True)


def setup():
    stdout, stderr = setup_config.communicate()
    print(stdout.decode(), stderr.decode(), flush=True)
    if setup_config.returncode != 0:
        raise Exception('encountered an error while setting up solana ')
    print('successfully set up Solana cli ')
    return True

setup()
