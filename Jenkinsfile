node ('master') {
    try {
        stage ('checkout scm') {
            checkout scm
        }

        stage('run dos2unix') {
            sh 'find . -type f -print0 | xargs -0 dos2unix'
        }

        stage('Remove name from licence') {
            sh 'sed -i "s/Philip Woldhek/Crucified Midget/g" MEGAabuse.py'
        }

        stage ('lint dockerfile') {
            def baseDir = System.getProperty("user.dir");
            docker.image('hadolint/hadolint:latest-debian').withRun('-v ${baseDir}/Dockerfile:/Dockerfile') { c ->
                docker.image('hadolint/hadolint:latest-debian').inside() {
                    sh 'hadolint Dockerfile | tee -a hadolint_lint.txt'
                    archiveArtifacts 'hadolint_lint.txt'
                }
            }
        }

        stage ('Pylint') {
            sh 'pylint --disable=W1202 --output-format=parseable --reports=no MEGAabuse.py > pylint.log || echo "pylint exited with $?"'

            step ([
                    $class                     : 'WarningsPublisher',
                    parserConfigurations       : [[
                                                          parserName: 'PYLint',
                                                          pattern   : 'pylint.log'
                                                 ]],
                    unstableTotalAll           : '0',   
                    usePreviousBuildAsReference: true
            ])
        }

        stage ('Create packages') {
            sh 'mkdir -p {windows,linux,mac}/binaries'
            sh 'echo windows linux mac | xargs -n 1 cp requirements.txt MEGAabuse.py guerrillamail.py'
            
            parallel (
                windows: {
                    sh 'cp -r binaries/megacmd_windows windows/binaries/'
                    sh 'cp -r binaries/megatools_win windows/binaries/'
                },
                linux: {
                    sh 'cp -r binaries/megacmd_linux linux/binaries/'
                    sh 'cp -r binaries/megatools_linux linux/binaries/'
                },
                mac: {
                    sh 'cp -r binaries/megacmd_mac mac/binaries/'
                    sh 'cp -r binaries/megatools_mac mac/binaries/'
                },
            )

        }

        stage ("Upload packages") {
            sh 'mkdir abuse'

            sh 'tar -zcvf abuse/windows.tar.gz windows'
            sh 'tar -zcvf abuse/linux.tar.gz linux'
            sh 'tar -zcvf abuse/mac.tar.gz mac'

            sh 'chmod +x binaries/megatools_linux/megatools'
            sh 'chmod +x binaries/megacmd_linux/*'
            
            sh 'python MEGAabuse.py -d MEGAabuse'
            archiveArtifacts 'out.txt'
        }
    }

    catch (err) {
        println(err.toString())
        error(err.getMessage())
        currentBuild.result = 'FAILED'
        exception_msg = err.getMessage();
    }

    finally {
        stage ('Clean Workspace') {
            cleanWs()
        }
    }
}