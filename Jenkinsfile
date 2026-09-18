pipeline {
    agent any
    environment {
        IMAGE_NAME = "url-shortener:${env.GIT_COMMIT.take(7)}"
        PYTEST_IMAGE_NAME = "${IMAGE_NAME}-test"
        PYTEST_CONTAINER_NAME = "pytest-ci"
    }
    stages {
        stage('Lint') {
            agent{
                docker {
                    image 'ghcr.io/astral-sh/ruff:0.16.7-alpine'
                    args '--entrypoint= '
                    reuseNode true
                }
            }
            
            steps { 
                sh '''
                    set +e
                    ruff format --check --output-format=junit > ruff-format.xml .
                    ruff check --output-format=junit --output-file=ruff-lint.xml .
                    exit 0
                '''
            }

            post {
                always { junit allowEmptyResults: true, testResults: 'ruff-format.xml, ruff-lint.xml'}
            }
        }

        stage('Pytest') {
            steps {
                script {
                    docker.build("${env.PYTEST_IMAGE_NAME}", "-f Dockerfile --target tests .")
                    sh """
                    docker run \
                        --name ${env.PYTEST_CONTAINER_NAME} \
                        ${env.PYTEST_IMAGE_NAME} \
                        pytest -q --junitxml=/app/results.xml
                    docker cp ${env.PYTEST_CONTAINER_NAME}:/app/results.xml pytest.xml
                    """
                }
            }

            post {
                always { junit testResults: 'pytest.xml'}
                cleanup { sh "docker container rm ${env.PYTEST_CONTAINER_NAME}" }
            }
        }

        stage('Build') {
            steps {
                script {
                    def short_hash = env.GIT_COMMIT.take(7)
                    env.IMAGE_TAG = short_hash
                    docker.build("${IMAGE_NAME}", "-f Dockerfile .")
                }
            }
        }

        stage('Image scan') {
            agent {
                docker {
                    image 'aquasec/trivy:0.74.0'
                    args '--entrypoint= ' +
                        '-v /var/run/docker.sock:/var/run/docker.sock ' +
                        '--group-add 989 '
                    reuseNode true
                }
            }
            
            steps {
                sh '''
                    trivy image \
                        --cache-dir $WORKSPACE/.trivycache \
                        --format template \
                        --template "@/contrib/junit.tpl" \
                        --severity HIGH,CRITICAL \
                        -o trivy.xml \
                        ${IMAGE_NAME}
                '''
            }
            
            post {
                always { junit allowEmptyResults: true, testResults: 'trivy.xml' }
            }
        }

        stage('publish') {
            steps {
                echo 'Publishing image...'
            }
        }
    }
}