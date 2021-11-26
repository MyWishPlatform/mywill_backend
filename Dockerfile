FROM python:3.7

RUN pip install -r requirements.txt || true
# этого добра просто нет в requirements.txt и оно там не появляется
RUN pip install py_ecc
# доустанавливаем зависимости, игнорируя конфликты версий
RUN pip install -r requirements.txt --no-deps || true

#RUN mkdir temp

# установка ярна для компиляции контрактов
#RUN npm install -g yarn

# ставим говнозависимось для работы airdrop-contract (./contracts/airdrop-contract)
RUN pip install git+https://chromium.googlesource.com/external/gyp

WORKDIR /app
COPY . /app
