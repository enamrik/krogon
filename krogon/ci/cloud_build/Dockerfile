FROM python

USER root

COPY . /krogon

WORKDIR ~

ENV KROGON_INFRA_CACHE ~/.infra_cache

RUN pip install /krogon

CMD ['krogon']