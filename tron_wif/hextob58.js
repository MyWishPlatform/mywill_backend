const TronWeb = require('tronweb');
const HttpProvider = TronWeb.providers.HttpProvider;

const fullNode = new HttpProvider('https://api.trongrid.io');
const solidityNode = new HttpProvider('https://api.trongrid.io');
const eventServer = 'https://api.trongrid.io/';
const baseHex = process.argv[2]

const app = async () => {
    const tronWeb = new TronWeb(
        fullNode,
        solidityNode,
        eventServer
    );

    tronWeb.setDefaultBlock('latest');
    const tob58 = tronWeb.address.fromHex(baseHex)
    if (tronWeb.isAddress(tob58)) {
        console.log(tob58)    
    } else {
        console.log('decoding error')
    }
};

app()