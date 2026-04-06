#!groovy
import groovy.json.JsonBuilder
import groovy.json.JsonSlurperClassic

pipeline {
    agent any
    parameters {
        text(name: 'JSON', description: 'JSON с параметрами запуска', defaultValue: '')
    }

    environment {
        DATE_TIME_NOW = "${new Date().format('yyyy-MM-dd_HH-mm-ss')}"
    }

    stages {
        stage("Starting Tests") {
            when {
                expression { params.JSON != '' }
            }
            steps {
                script {
                    currentBuild.displayName = "START: ${env.DATE_TIME_NOW} #${env.BUILD_NUMBER}"
                    def runTestTasksList = new JsonSlurperClassic().parseText(params.JSON)
                    def parallelJobsMap = [:]

                    runTestTasksList.eachWithIndex { profile, index ->
                        parallelJobsMap["run-tests-${index}"] = {
                            build job: 'test_runner',
                                    parameters: [
                                            text(name: 'GENERATORS', value: ''),
                                            text(name: 'JSON', value: new JsonBuilder(profile).toString())
                                    ]
                        }
                    }
                    parallel parallelJobsMap
                }
            }
        }
    }
}
