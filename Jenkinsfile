multibranchPipeline {
    agent any
    stages {
        stage('linting') {
            echo 'Linting'
        }

        stage('tests') {
            echo 'Running pytest tests...'
        }

        stage('bulid') {
            echo 'Building docker image...'
        }

        stage('image-scan') {
            echo 'Scanning built image...'
        }

        stage('publish') {
            echo 'Publishing image...'
        }
    }
}