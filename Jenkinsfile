pipeline {
    agent any
    environment {
        IMAGE_REPO = "url-shortener"
        IMAGE_TAG = "${env.GIT_COMMIT.take(7)}"
        IMAGE_NAME = "${DOCKERHUB_USERNAME}/${IMAGE_REPO}:${IMAGE_TAG}"

        PYTEST_IMAGE_NAME = "${IMAGE_NAME}-pytest"
        PYTEST_CONTAINER_NAME = "pytest-${IMAGE_REPO}-${IMAGE_TAG}"
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
                cleanup { 
                    sh "docker container rm ${PYTEST_CONTAINER_NAME} && docker rmi ${PYTEST_IMAGE_NAME}"  
                }
            }
        }

        stage('Build') {
            steps {
                script {
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
                sh """
                    trivy image \
                        --cache-dir $WORKSPACE/.trivycache \
                        --format template \
                        --template "@/contrib/junit.tpl" \
                        --severity HIGH,CRITICAL \
                        -o trivy.xml \
                        ${IMAGE_NAME}
                """
            }
            
            post {
                always { junit allowEmptyResults: true, testResults: 'trivy.xml' }
            }
        }

        stage('publish') {
            when {
                branch 'bumping_tag'
            }
            steps {
                script {
                    docker.withRegistry('https://index.docker.io/v1/', 'dockerhub') {
                        docker.image("${IMAGE_NAME}").push("${IMAGE_TAG}")
                    }
                }
            }
        }
        
        stage('image tag bump') {
            when {
                branch 'bumping_tag'
            }
            agent {
                docker {
                    image 'registry.k8s.io/kustomize/kustomize:v5.4.3'
                    args '--entrypoint='
                    reuseNode true
                }
            }   

            steps {
                withCredentials([usernamePassword(credentialsId: 'github-app',
                                          usernameVariable: 'GH_APP',
                                          passwordVariable: 'GH_TOKEN')]) {
                    sh '''
                        rm -rf k3d-gitops
                        git clone --depth 1 "https://x-access-token:${GH_TOKEN}@github.com/smallestcontainer/k3d-gitops.git" k3d-gitops
                        cd k3d-gitops
                        kustomize edit set image "${IMAGE_NAME}"
                        git add kustomization.yaml
                        git diff --cached --quiet && { echo "Tag ${IMAGE_TAG} already deployed"; exit 0; }
                        git -c user.name=jenkins -c user.email=jenkins@localhost \
                            commit -m "deploy url-shortener ${IMAGE_TAG}"
                        git push origin HEAD:master
                    '''
                }
            }
        }
    }

    post {
        cleanup {
            sh "docker rmi ${IMAGE_NAME}"
        }
    }
}