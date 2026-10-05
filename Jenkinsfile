// ============================================================================
// DevOps Pulse — Jenkins CI/CD pipeline
//
//   Checkout → Install Dependencies → Test → Build Frontend
//            → Build Docker Image → Deploy to Kubernetes → Verify Deployment
//
// Each stage consumes the output of the previous one:
//   Git commit  ──►  tested code  ──►  Docker image devops-pulse:<BUILD_NUMBER>
//   ──►  Kubernetes Deployment rolls out that image  ──►  Prometheus scrapes the
//   new Pods  ──►  Grafana / the dashboard show the new version and build number.
//
// Agent requirements (provided by jenkins/Dockerfile): python3, node/npm,
// docker CLI pointed at Minikube's Docker daemon, kubectl with a kubeconfig.
// ============================================================================
pipeline {
    agent any

    // "Jenkins detects change": poll the Git repository every ~2 minutes.
    // (A GitHub webhook can replace this when Jenkins is reachable from the internet.)
    triggers {
        pollSCM('H/2 * * * *')
    }

    options {
        timestamps()
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '15'))
        timeout(time: 30, unit: 'MINUTES')
    }

    environment {
        APP_NAME      = 'devops-pulse'
        APP_VERSION   = '1.0.0'
        K8S_NAMESPACE = 'devops-pulse'
        // Every build produces a uniquely tagged, traceable image
        IMAGE         = "devops-pulse:${env.BUILD_NUMBER}"
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                script {
                    env.COMMIT_SHA   = sh(returnStdout: true, script: 'git rev-parse HEAD').trim()
                    env.COMMIT_SHORT = env.COMMIT_SHA.take(7)
                }
                sh 'git log -1 --pretty=format:"Commit %h by %an: %s"'
            }
        }

        stage('Install Dependencies') {
            parallel {
                stage('Backend (pip)') {
                    steps {
                        dir('backend') {
                            sh '''
                                python3 -m venv .venv
                                . .venv/bin/activate
                                pip install --quiet -r requirements-dev.txt
                            '''
                        }
                    }
                }
                stage('Frontend (npm)') {
                    steps {
                        dir('frontend') {
                            sh 'npm ci --no-audit --no-fund'
                        }
                    }
                }
            }
        }

        stage('Test') {
            parallel {
                stage('Backend tests (pytest)') {
                    steps {
                        dir('backend') {
                            sh '. .venv/bin/activate && pytest --junitxml=test-results/junit.xml'
                        }
                    }
                    post {
                        always {
                            junit 'backend/test-results/junit.xml'
                        }
                    }
                }
                stage('Frontend tests (vitest)') {
                    steps {
                        dir('frontend') {
                            sh 'npm test'
                        }
                    }
                }
            }
        }

        stage('Build Frontend') {
            // Type-check + production build. Fails fast here, before the slower
            // Docker build (which rebuilds the frontend in a clean stage).
            steps {
                dir('frontend') {
                    sh 'npm run build'
                }
            }
        }

        stage('Build Docker Image') {
            steps {
                sh '''
                    docker build \
                      --build-arg APP_VERSION=${APP_VERSION} \
                      --build-arg BUILD_NUMBER=${BUILD_NUMBER} \
                      --build-arg GIT_COMMIT=${COMMIT_SHA} \
                      --build-arg BUILD_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ) \
                      --build-arg IMAGE_NAME=${IMAGE} \
                      -t ${IMAGE} \
                      -t ${APP_NAME}:latest \
                      .
                    docker image ls ${APP_NAME}
                '''
            }
        }

        stage('Deploy to Kubernetes') {
            steps {
                sh '''
                    kubectl apply -f k8s/namespace.yaml
                    kubectl apply -f k8s/
                    kubectl -n ${K8S_NAMESPACE} set image deployment/${APP_NAME} ${APP_NAME}=${IMAGE}
                    kubectl -n ${K8S_NAMESPACE} annotate deployment/${APP_NAME} --overwrite \
                      kubernetes.io/change-cause="Jenkins build #${BUILD_NUMBER} (commit ${COMMIT_SHORT})"
                '''
            }
        }

        stage('Verify Deployment') {
            steps {
                sh '''
                    kubectl -n ${K8S_NAMESPACE} rollout status deployment/${APP_NAME} --timeout=180s
                    kubectl -n ${K8S_NAMESPACE} get deployment,pods,svc -o wide

                    # Smoke test through the Kubernetes Service from inside the cluster:
                    # the app must be healthy AND report the build number we just deployed.
                    # (Retries cover the few seconds old Pods need to leave the Service.)
                    kubectl -n ${K8S_NAMESPACE} exec deploy/${APP_NAME} -- python -c "
import json, time, urllib.request
base = 'http://devops-pulse-service'
for attempt in range(1, 11):
    try:
        health = json.load(urllib.request.urlopen(base + '/health', timeout=5))
        deploy = json.load(urllib.request.urlopen(base + '/api/deployment', timeout=5))
        print('attempt', attempt, '| health:', health['status'], '| build:', deploy['build_number'], '| image:', deploy['image'])
        if health['status'] == 'healthy' and deploy['build_number'] == '${BUILD_NUMBER}':
            break
    except OSError as exc:
        print('attempt', attempt, 'failed:', exc)
    time.sleep(3)
else:
    raise SystemExit('Build ${BUILD_NUMBER} is not serving healthy traffic through the Service')
"
                    kubectl -n ${K8S_NAMESPACE} rollout history deployment/${APP_NAME} | tail -n 3
                '''
            }
        }
    }

    post {
        success {
            echo "SUCCESS: ${IMAGE} (commit ${env.COMMIT_SHORT}) is live in namespace ${K8S_NAMESPACE}"
        }
        failure {
            echo 'FAILURE: collecting Kubernetes diagnostics'
            sh '''
                kubectl -n ${K8S_NAMESPACE} get pods -o wide || true
                kubectl -n ${K8S_NAMESPACE} describe deployment/${APP_NAME} | tail -n 25 || true
                kubectl -n ${K8S_NAMESPACE} get events --sort-by=.lastTimestamp | tail -n 20 || true
            '''
        }
    }
}
