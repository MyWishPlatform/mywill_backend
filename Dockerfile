# Pull base image
FROM python:3.8

# Set environment varibles
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update -y && apt-get upgrade -y
RUN apt-get install -y vim nano libleveldb-dev python3-setuptools redis-server

ENV WORK_DIR /code

# Set work directory
RUN mkdir $WORK_DIR
WORKDIR $WORK_DIR

# Copy project
COPY . $WORK_DIR

# Install dependencies
RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt --no-deps