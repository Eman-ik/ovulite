pipeline {
    agent any

    environment {
        TEST_REPO = 'https://github.com/eman-ik/ovulite-selenium-test.git'
        BASE_URL = 'http://localhost:5174'
        SENDER_EMAIL = 'emanmalik164@gmail.com'
    }

    stages {

        stage('Checkout Application Code') {
            steps {
                checkout scm
            }
        }

        stage('Start Ovulite Application') {
            steps {
                sh '''
                docker compose down || true
                docker compose up -d --build
                sleep 60
                '''
            }
        }

        stage('Clone Selenium Tests') {
            steps {
                sh '''
                rm -rf ovulite-selenium-tests
                git clone ${TEST_REPO}
                '''
            }
        }

        stage('Run Selenium Tests') {
            steps {
                sh '''
                cd ovulite-selenium-tests

                docker run --rm \
                    --network host \
                    -v "$PWD":/usr/src/app \
                    -w /usr/src/app \
                    -e BASE_URL=${BASE_URL} \
                    markhobson/maven-chrome \
                    mvn clean test
                '''
            }
        }
    }

    post {

        always {

            emailext(
                subject: "Ovulite Jenkins Test Results - ${currentBuild.currentResult}",
                body: """
                Build Result: ${currentBuild.currentResult}

                Jenkins pipeline executed successfully.

                Project: ${env.JOB_NAME}
                Build Number: ${env.BUILD_NUMBER}
                """,
                to: "YOUR-GMAIL@gmail.com",
                from: "${SENDER_EMAIL}"
            )

            sh '''
            docker compose down || true
            '''
        }
    }
}