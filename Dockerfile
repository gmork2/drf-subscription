FROM python:3.8
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
WORKDIR /usr/src/app
RUN pip install --upgrade pip
COPY requirements_dev.txt /usr/src/app/
RUN pip install -r requirements_dev.txt
COPY entrypoint.sh /usr/src/app/
COPY . /usr/src/app/
ENTRYPOINT ["/usr/src/app/entrypoint.sh"]
