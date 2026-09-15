pipeline {
    agent none
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
                echo 'Building docker image...'
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