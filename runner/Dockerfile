# One image for every place the runner executes (local, Cloud Run, Bitbucket Pipelines).
# JDK 8 builds old Apache Commons Lang commits; the harness runs inside it without Docker.
FROM eclipse-temurin:8-jdk

RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 git ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Full history of the project under test, as published by Apache.
RUN git clone --bare --quiet https://github.com/apache/commons-lang.git /opt/commons-lang.git

# Test-time libraries (JUnit 4.12, Hamcrest 1.3, EasyMock 3.2, Commons IO 2.4, JCIP, JSR-305).
COPY .cache/lib/ /opt/deps/
COPY harness/ /opt/app/harness/
COPY benchmark/ /opt/app/benchmark/

ENV RUNNER_MODE=local \
    RUNNER_LIB=/opt/deps \
    RUNNER_GIT=/opt/commons-lang.git \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /opt/app/harness
CMD ["python3", "selfcheck.py"]
