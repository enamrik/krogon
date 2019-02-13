FROM python

USER root

COPY . /krogon

WORKDIR ~

ENV KROGON_INFRA_CACHE ~/.infra_cache

RUN pip install -e /krogon

CMD ['krogon']