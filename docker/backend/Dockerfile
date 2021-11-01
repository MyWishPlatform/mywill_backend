FROM 0nliner/mywish_backend__base_container:1.0
#FROM node:6.7.0

#RUN mkdir temp

# установка ярна для компиляции контрактов
#RUN npm install -g yarn

CMD ["gunicorn", "-c", "gunicorn.conf.py", "lastwill.wsgi:application", "--preload"]
#CMD ["python", "manage.py", "runserver"]

EXPOSE 8000
