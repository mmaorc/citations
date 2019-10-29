# Buster is needed in order to be able to compile graphviz
FROM python:3.7-slim-buster

RUN apt-get update

RUN apt-get install -y build-essential \
    graphviz-dev \
    graphviz

COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

RUN pip install pydot


ADD . /myapp
WORKDIR /myapp

ENV PATH="/opt/gtk/bin:${PATH}"


ENTRYPOINT ["python", "graph.py"]
CMD ["--help"]
