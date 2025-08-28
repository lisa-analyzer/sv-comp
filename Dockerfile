# Start from a Python base image
FROM python:3.13-slim

ENV JLISA="jlisa-1.0-SNAPSHOT.zip"
ENV SVCOMP="svcomp-benchmarks-main.zip"

# Install Java 25 from apt
RUN apt-get update &&\
	apt-get install -y openjdk-25-jre &&\
	apt-get install -y unzip

# Set JAVA_HOME and update PATH
ENV JAVA_HOME=/usr/lib/jvm/java-25-openjdk-amd64
ENV PATH=$JAVA_HOME/bin:$PATH

# Create a working directory
WORKDIR /app

# Copy files from host → container
COPY main.py ./
COPY pyproject.toml ./
COPY requirements.txt ./
COPY config_dockerfile.json ./config.json
COPY run_statistics_dockerfile.sh ./run_statistics.sh
RUN chmod 777 ./run_statistics.sh
COPY cli/ ./cli
COPY vendor/vendorize.py ./vendor/
COPY vendor/package_loader.py ./vendor/

COPY ${JLISA} ./jlisa/jlisa.zip
RUN unzip ./jlisa/jlisa.zip -d ./jlisa/
RUN rm ./jlisa/jlisa.zip
COPY ${SVCOMP} ./svcomp-benchmark/svcomp.zip
RUN unzip ./svcomp-benchmark/svcomp.zip -d ./svcomp-benchmark/
RUN rm ./svcomp-benchmark/svcomp.zip
RUN mkdir ./output
RUN python ./vendor/vendorize.py
CMD ./run_statistics.sh