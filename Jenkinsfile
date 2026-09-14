pipeline {
    agent any
    stages {
        stage('linting') {
            steps { 
                echo 'Linting'
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