FROM python:3.7

WORKDIR /app

ENV PYTHONUNBUFFERED=1

COPY requirements.txt /app/requirements.txt

RUN pip install -r requirements.txt || true
# этого добра просто нет в requirements.txt и оно там не появляется
RUN pip install py_ecc
# доустанавливаем зависимости, игнорируя конфликты версий
RUN pip install -r requirements.txt --no-deps || true

# ставим зависимость для работы airdrop-contract (./contracts/airdrop-contract)
RUN pip install git+https://chromium.googlesource.com/external/gyp

# устанавливаем модуль near из нашего репозитория
RUN pip install git+https://github.com/MyWishPlatform/near-api-py.git@master

RUN wget https://github.com/eosio/eos/releases/download/v2.1.0/eosio_2.1.0-1-ubuntu-20.04_amd64.deb

RUN apt update

RUN apt -y install ./eosio_2.1.0-1-ubuntu-20.04_amd64.deb

# npm для установки тулзы командной строки для near
RUN apt -y install npm

RUN npm install -g near-cli

COPY . /app
