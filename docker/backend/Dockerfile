FROM python:3.7
#FROM node:6.7.0

WORKDIR /app
COPY . /app

# setting up python backend

RUN pip install -r requirements.txt || true
# этого добра просто нет в requirements.txt и оно там не появляется
RUN pip install py_ecc
RUN pip install gunicorn
# доустанавливаем зависимости, игнорируя конфликты версий
RUN pip install -r requirements.txt --no-deps || true

#RUN mkdir temp

# установка ярна для компиляции контрактов
#RUN npm install -g yarn

# ставим говнозависимось для работы airdrop-contract (./contracts/airdrop-contract)
RUN pip install git+https://chromium.googlesource.com/external/gyp


#FROM node:6.7.0

#RUN mkdir temp

# установка ярна для компиляции контрактов
#RUN npm install -g yarn

CMD ["gunicorn", "-c", "/app/lastwill/secret/gunicorn.conf.py", "lastwill.wsgi:application", "--preload"]

EXPOSE 8000
