#!groovy
import groovy.json.JsonBuilder
import groovy.json.JsonSlurperClassic

import java.text.SimpleDateFormat

class Run {
    String LOAD_GENERATOR
    String ENV
    String TEST_NAME
    String SIMULATION_CLASS
}

class Steps {
    Double TPS
    Double RAMP_TIME
    Double HOLD_TIME
}

class Profile {
    String SCENARIO_NAME
    String PACING
    Steps[] STEPS
}

class TestParam {
    Run RUN
    Profile[] PROFILE
    Map PROPERTIES
}

class RunSettings {
    String PROFILE_NAME
    String SYSTEM_NAME
    String LEVEL_CONSOLE_LOG
    String LEVEL_FILE_LOG
    String DATASOURCE_HOST
    Integer DATASOURCE_PORT
    Double PERCENT_PROFILE
}

class CommonSettings {
    RunSettings RUN_SETTINGS
    Map PROPERTIES
}

class TestsParam {
    TestParam[] TESTS_PARAM
    CommonSettings COMMON_SETTINGS
}

// GENERATORS SYSTEM
// [
//   ""
//   ""
//]

def groupedMap = [:]

def dateFormat(long timeSec) {
    long days = timeSec / 86_400
    long remainder = timeSec % 86_400
    long hours = remainder / 3_600
    remainder %= 3_600
    long min = remainder / 60
    long sec = remainder % 60

    return String.format("%02d d. %02d h. %02d m. %02d s.", days, hours, min, sec)
}

def scenarioDurationMax(system, profileName, testsParam) {
    def profile = (testsParam?.TESTS_PARAM ?: [])
            .collectMany { testParam -> testParam?.PROFILE ?: [] }
            .findAll { it != null }
            .max { profile ->
                profile?.STEPS?.collect { step ->
                    ((step?.RAMP_TIME ?: 0) + (step?.HOLD_TIME ?: 0)) * 60
                }?.sum() ?: 0
            }

    def durationProfile = profile?.STEPS?.collect { step ->
        (((step?.RAMP_TIME ?: 0) + (step?.HOLD_TIME ?: 0)) * 60) as int
    }?.sum() ?: 0

    def sdfDateTime = new SimpleDateFormat('yyyy-MM-dd_HH-mm-ss')
    sdfDateTime.setTimeZone(TimeZone.getTimeZone('Europe/Moscow'))

    def calendarStartRumpUp = Calendar.getInstance()
    def calendarStart = Calendar.getInstance()
    def calendarEnd = Calendar.getInstance()
    calendarStart.add(Calendar.SECOND, (int) ((profile?.STEPS?.get(0)?.RAMP_TIME ?: 0) * 60))
    calendarEnd.add(Calendar.SECOND, durationProfile)
    long seconds = (calendarEnd.getTimeInMillis() - calendarStartRumpUp.getTimeInMillis()) / 1000

    List<String> stepLongs = new ArrayList<>()
    def stepStart = (Calendar) calendarStartRumpUp.clone()

    for (int i = 0; i < (profile?.STEPS?.size() ?: 0); i++) {
        def step = profile.STEPS.get(i)
        stepStart.add(Calendar.SECOND, (int) (step.RAMP_TIME * 60))
        def stepEnd = (Calendar) stepStart.clone()
        stepEnd.add(Calendar.SECOND, (int) (step.HOLD_TIME * 60))
        stepLongs.add(String.format("from=%d&to=%d", stepStart.getTime(), getTime(), stepEnd.getTime().getTime()))
        stepStart = stepEnd
    }

    def description = new StringBuilder()
    description << System.lineSeparator()
    description << String.format('Test Duration: %-50.50s', dateFormat(seconds)) << System.lineSeparator()
    description << String.format('Grafana (RumpUp): %-50.50s', "&from=" + calendarStartRumpUp.getTime().getTime() + "&to=" + calendarEnd.getTime().getTime()) << System.lineSeparator()
    description << String.format('Grafana %-50.50s', "&from=" + calendarStart.getTime().getTime() + "&to=" + calendarEnd.getTime().getTime()) << System.lineSeparator()
    for (int i = 0; i < stepLongs.size(); i++) {
        description << String.format("Step #%-3.3s %-50.50s", i + 1, stepLongs.get(i)) << System.lineSeparator()
    }

    currentBuild.displayName = "SYSTEM: ${system} START: ${env.DATE_TIME_NOW} END: ~${new Date(new Date().time + ((long) durationProfile + 1) * 1000).format("yyyy-MM-dd_HH-mm-ss")} #${env.BUILD_NUMBER}"
    currentBuild.description = "PROFILE NAME: ${profileName} ${currentBuild.description}${description.toString()}"
}

pipeline {
    // master
    agent any
    parameters {
//        booleanParam(name: 'BUILD_JAR_ENABLE', defaultValue: false, description: 'Нужно ли пересобрать обновить исходники на генераторе')
//        string(name: 'GIT_BRANCH', defaultValue: 'master', description: 'Название ветки из которой надо подтянуть изменения')
        text(name: 'GENERATORS', defaultValue: '', description: 'JSON генераторов на которых надо обновить файлы и папки')
        text(name: 'JSON', defaultValue: '', description: 'JSON с параметрами запуска')
    }

    environment {
        LOG_FOLDER_PATH = 'logs'
        JAR_NAME = 'performance-test-gatling.jar'
        DATE_NOW = "${new Date().format('yyyy-MM-dd')}"
        DATE_TIME_NOW = "${new Date().format('yyyyy-MM-dd_HH-mm-ss')}"
//        GIT_URL = 'https://github.com/yourorg/yourrepo.git'
    }

    stages {
        stage("1. Prepare Tests") {
            when {
                expression { params.GENERATORS == '' }
            }
            steps {
                script {
                    def loadGeneratorList = new JsonSlumperClassic().parseText(params.GENERATORS)
                    currentBuild.displayName = "UPDATE FILES TO GENERATOR - ${env.DATE_TIME_NOW} #${env.BUILD_NUMBER}"
                    currentBuild.description = "GENERATORS: ${loadGeneratorList}"

                    def filesName = {
                        // Jar
                        'performance-test-gatling.jar'
                        // Папка
                        'env'
                        // Папка
                        'ssl_kafka'
                    }

                    def flagError = false
                    filesName.each { item ->
                        if (!fileExists(item)) {
                            flagError = true
                            println "No File Or Folder: ${item}"
                        }
                    }

                    if (flagError) {
                        throw new Exception('Error File Or Folder Not Found!')
                    }

                    stash(name 'testFileOrFolder', includes: 'performance-test-gatling.jar, env/**, ssl_kafka/**')

                    println '1. Preparing Tests Folders And File On Generators'
                    def prepareTasks = [:]
                    loadGeneratorList.eachWithIndex { loadGenerator, index ->
                        prepareTasks["${index}-prepare-generator-folder-and-file-(${loadGenerator})"] = {
                            node(loadGenerator) {
                                println "Preparing Load Generator: ${loadGenerator}"

                                // Обновление файлов и папок на генераторах нагрузки
                                unstash('testFileOrFolder')
                            }
                        }
                    }
                    parallel prepareTasks
                }
            }
        }

        // Запуск тестов
        stage("2. Starting Tests") {
            when {
                expression { params.JSON != '' }
            }
            steps {
                script {
                    println '=========== RUN TESTS ON GENERATORS ==========='
                    def parsed = new JsonSlurperClassic().parseText(params.JSON)
                    def commonSettings = parsed.COMMON_SETTINGS
                    def preparedTasks = [:]
                    def prepareTasks = [:]
                    def runTestTasks = [:]
                    scenarioDurationMax(commonSettings.BUILD_SETTINGS.SYSTEM_NAME, commonSettings.BUILD_SETTINGS.PROFILE_NAME, parsed)

                    println '1. Group Tests By LOAD_GENERATOR'
                    parsed.TESTS_PARAM.each { testParam ->
                        def loadGenerator = testParam.RUN?.LOAD_GENERATOR
                        if (!groupedMap.containsKey(loadGenerator)) {
                            groupedMap[loadGenerator] = [TESTS_PARAM: [], COMMON_SETTINGS: commonSettings]
                        }
                        groupedMap[loadGenerator].TESTS_PARAM << testParam
                    }

                    println '2. Preparing The Launch Script'
                    groupedMap.each { loadGenerator, testProfile ->
                        def cleanProfile = [
                                TESTS_PARAM    : testProfile.TESTS_PARAM.collect { testParam ->
                                    [RUN: testParam.RUN, PROFILE: testParam.PROFILE, PROPERTIES: testParam.PROPERTIES]
                                },
                                COMMON_SETTINGS: testProfile.COMMON_SETTINGS
                        ]

                        def profileJson = new JsonBuilder(cleanProfile).toString()
                        def profilePath = "profiles/test_profile_${loadGenerator}.json"
                        def scriptRun = "java " +
                                "-DSYSTEM_NAME=${testProfile.COMMON_SETTINGS.RUN_SETTINGS.SYSTEM_NAME} " +
                                "-DLOAD_GENERATOR=${loadGenerator} " +
                                "-DDATASOURCE_HOST=${testProfile.COMMON_SETTINGS.RUN_SETTINGS.DATASOURCE_HOST} " +
                                "-DDATASOURCE_PORT=${testProfile.COMMON_SETTINGS.RUN_SETTINGS.DATASOURCE_PORT} " +
                                "-DLEVEL_CONSOLE_LOG=${testProfile.COMMON_SETTINGS.RUN_SETTINGS.LEVEL_CONSOLE_LOG} " +
                                "-DLEVEL_FILE_LOG=${testProfile.COMMON_SETTINGS.RUN_SETTINGS.LEVEL_FILE_LOG} " +
                                "-DLOG_FILE_NAME=test_run_${loadGenerator} " +
                                "-DDATE_NOW=${env.DATE_NOW} " +
                                "-DDATE_TIME_NOW=${env.DATE_TIME_NOW} " +
                                "-DPROFILE=${profilePath} -cp performance-test-gatling.jar io.gatling.app.Gatling -s ru.gatling.TestRunner"

                        preparedTasks[loadGenerator] = [
                                profileJson: profileJson,
                                scriptRun  : scriptRun,
                                profilePath: profilePath
                        ]
                    }

                    println '3. Preparing Tests On Generators'
                    preparedTasks.eachWithIndex { loadGenerator, taskData, index ->
                        prepareTasks["${index}-prepare-generator-(${loadGenerator})"] = {
                            node(loadGenerator) {
                                println "Preparing Profile On Load Generator: ${loadGenerator}"

                                // Сохраняем JSON профиль в файл
                                sh 'mkdir -p profiles'
                                sh "echo '${taskData.profileJson}' > ${taskData.profilePath}"
                            }
                        }
                    }
                    parallel prepareTasks

                    println '4. Running Tests On Generators'
                    preparedTasks.eachWithIndex { loadGenerator, taskData, index ->
                        runTestTasks["${index}-run-tests-generator-(${loadGenerator})"] = {
                            node(loadGenerator) {
                                println "Running Load Generator: ${loadGenerator}"
                                println "Command: ${taskData.scriptRun}"

                                // Запускаем тест на генераторе
                                sh "${taskData.scriptRun}"
                            }
                        }
                    }
                    parallel runTestTasks
                }
            }
        }
    }

    post {
        always {
            script {
                println '=========== CREATE LOG FOLDER JENKINS ==========='
                groupedMap.eachWithIndex { generator, testProfile, index ->
                    node(generator) {
                        try {
                            println '1. Archive Test Artifacts'
                            archiveArtifacts artifacts: "${env.LOG_FOLDER_PATH}/**", allowEmptyArchive: true
                        } catch (Exception e) {
                            println "Failed To Archive Test Artifacts: ${e.message}"
                            e.printStackTrace()
                        }

                        try {
                            println '2. Delete Test Logs Folder And Profiles'
                            sh "rm -rf ${env.LOG_FOLDER_PATH} profiles/*"
                        } catch (Exception e) {
                            println "Failed To Delete Test Logs Folder: ${e.message}"
                            e.printStackTrace()
                        }
                    }
                }
            }
        }

        unsuccessful {
            script {
                println '=========== STOP JAVA PROCESS ON GENERATORS ==========='
                groupedMap.eachWithIndex { generator, testProfile, index ->
                    try {
                        node(generator) {
                            println "${index}. Kill Process Generator - ${generator}"
                            sh "sudo kill \$(pgrep -f ${testProfile.COMMON_SETTINGS.RUN_SETTINGS.PROFILE_NAME})"
                        }
                    } catch (Exception e) {
                        println "Failed To Kill Process On Generator ${generator}: ${e.message}"
                        e.printStackTrace()
                    }
                }
            }
        }
    }
}