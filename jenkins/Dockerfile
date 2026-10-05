# Jenkins controller with every tool the DevOps Pulse pipeline needs.
# Built and started by jenkins/setup-jenkins.ps1
FROM jenkins/jenkins:lts-jdk17

USER root

# Python (backend tests), git, curl
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python3-venv python3-pip git curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Node.js 20 (frontend install / tests / build)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
 && apt-get install -y --no-install-recommends nodejs \
 && rm -rf /var/lib/apt/lists/*

# Docker CLI + buildx (talks to Minikube's Docker daemon via DOCKER_HOST)
COPY --from=docker:27-cli /usr/local/bin/docker /usr/local/bin/docker
COPY --from=docker:27-cli /usr/local/libexec/docker/cli-plugins /usr/local/libexec/docker/cli-plugins

# kubectl (talks to Minikube's API server via KUBECONFIG)
RUN curl -fsSLo /usr/local/bin/kubectl \
      "https://dl.k8s.io/release/$(curl -fsSL https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" \
 && chmod +x /usr/local/bin/kubectl

USER jenkins

# Plugins + Configuration-as-Code (admin user and the pipeline job are created automatically)
COPY --chown=jenkins:jenkins plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli --plugin-file /usr/share/jenkins/ref/plugins.txt

COPY --chown=jenkins:jenkins casc.yaml /usr/share/jenkins/ref/casc.yaml
ENV CASC_JENKINS_CONFIG=/usr/share/jenkins/ref/casc.yaml \
    JAVA_OPTS="-Djenkins.install.runSetupWizard=false"
