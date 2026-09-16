pipeline {
    agent none
    environment {
        IMAGE_NAME = "url-shortener"
    }
    stages {
        
        stage('Lint') {
            agent{
                docker {
                    image 'ghcr.io/astral-sh/ruff:0.16.7-alpine'
                    args '--entrypoint='
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

        stage('tests') {
            steps {
                echo 'Running pytest tests...'
            }
        }

        stage('bulid') {
            steps {
                script {
                    def image_hash = env.GIT_COMMIT.take(7)
                    def image = docker.build("${IMAGE_NAME}-$image_hash", "-f Dockerfile .")
                }
            }
        }

        stage('image-scan') {
            steps {
                echo 'Scanning built image...'
            }
        }

        stage('publish') {
            steps {
                echo 'Publishing image...'
            }
        }
    }
}