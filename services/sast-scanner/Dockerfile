FROM python:3.12-slim

WORKDIR /app

# Install git, Java (for sonar-scanner), and download sonar-scanner-cli
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl unzip default-jre-headless wget libicu-dev && \
    rm -rf /var/lib/apt/lists/*

# Install sonar-scanner CLI
ENV SONAR_SCANNER_VERSION=5.0.1.3006
RUN curl -sSLo /tmp/sonar-scanner.zip \
    https://binaries.sonarsource.com/Distribution/sonar-scanner-cli/sonar-scanner-cli-${SONAR_SCANNER_VERSION}-linux.zip && \
    unzip /tmp/sonar-scanner.zip -d /opt && \
    mv /opt/sonar-scanner-${SONAR_SCANNER_VERSION}-linux /opt/sonar-scanner && \
    rm /tmp/sonar-scanner.zip
ENV PATH="/opt/sonar-scanner/bin:${PATH}"

# Install .NET SDK for scanning C# projects
RUN wget https://dot.net/v1/dotnet-install.sh -O /tmp/dotnet-install.sh && \
    chmod +x /tmp/dotnet-install.sh && \
    /tmp/dotnet-install.sh --channel 8.0 --install-dir /usr/share/dotnet && \
    rm /tmp/dotnet-install.sh
ENV PATH="/usr/share/dotnet:${PATH}"
ENV DOTNET_ROOT="/usr/share/dotnet"

# Install dotnet-sonarscanner global tool
RUN dotnet tool install --global dotnet-sonarscanner
ENV PATH="/root/.dotnet/tools:${PATH}"

RUN addgroup --system appgroup && adduser --system --home /home/appuser --ingroup appgroup appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chown -R appuser:appgroup /app /home/appuser
USER appuser
ENV HOME=/home/appuser

EXPOSE 8001

CMD ["python", "worker.py"]
