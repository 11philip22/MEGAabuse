parallel (
    windows: {
        node ('WindowsAgent') {
            try {
                 stage ('checkout scm') {
                    checkout scm
                }           
            }
            
            catch() {
                println(err.toString())
                error(err.getMessage())
                currentBuild.result = 'FAILED'

                cleanWs()          
            }
        }    
    },
    unix: {
        node ('master') {
            try {
                 stage ('checkout scm') {
                    checkout scm
                }            
            }
            
            catch() {
                println(err.toString())
                error(err.getMessage())
                currentBuild.result = 'FAILED'

                cleanWs()          
            }    
        }
    },  
)

node ('master') {
    try {
        stage ('Lint dockerfile') {
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

            archiveArtifacts 'pylint.log'
        }
    }

    catch {
        println(err.toString())
        error(err.getMessage())
        currentBuild.result = 'FAILED'

        cleanWs()
    }
}

prallel (
    windows: {
        node ('WindowsAgent') {
            try {
                stage ('checkout scm') {
                    checkout scm
                }
                
                stage ('Create packages') {
                    powershell 'New-Item -ItemType Directory -Path ".\\windows"'
                    powershell 'Copy-Item -Path .\\requirements.txt,.\\MEGAabuse.py,.\\guerrillamail.py -Destination .\\windows'
                    powershell 'python.exe .\\setup.py build_exe'
                    powershell '''\
                    $env:Path += ";C:\\Program Files\\WinRAR\\"
                    rar a abuse.rar .\\build\\exe.win32-3.8
                    '''
                }

                // stage ('Upload package') {
                //     powershell 'New-Item -ItemType Directory -Path ".\\upload"'
                //     powershell 'Move-Item .\\abuse.rar .\\upload\\'
                //     powershell 'python.exe MEGAabuse.py -d .\\upload'
                // }               
            }

            catch {
                println(err.toString())
                error(err.getMessage())
                currentBuild.result = 'FAILED'
            }

            finally {
                stage ('Clean Workspace') {
                    cleanWs()
                }
            }
        }
    },
    unix: {
        node ('master') {
            try {
                stage ('Create packages') {
                    sh 'mkdir -p {linux,mac}/binaries'
                    sh 'echo linux mac | xargs -n 1 cp requirements.txt MEGAabuse.py guerrillamail.py'

                    parallel (
                        linux: {
                            sh 'cp -r binaries/megacmd_linux linux/binaries/'
                            sh 'cp -r binaries/megatools_linux linux/binaries/'
                        },
                        mac: {
                            sh 'cp -r binaries/megacmd_mac mac/binaries/'
                            sh 'cp -r binaries/megatools_mac mac/binaries/'
                        },
                    )

                    sh 'mkdir abuse'

                    sh 'tar -zcvf abuse/linux.tar.gz linux'
                    sh 'tar -zcvf abuse/mac.tar.gz mac'
                }

                // stage ('Upload package') {
                //     sh 'chmod +x binaries/megatools_linux/megatools'
                //     sh 'chmod +x binaries/megacmd_linux/*'
                //     sh 'python MEGAabuse.py -d abuse'
                    
                //     archiveArtifacts 'out.txt'
                // }                    
            }

            catch {
                println(err.toString())
                error(err.getMessage())
                currentBuild.result = 'FAILED'
            }

            finally {
                stage ('Clean Workspace') {
                    cleanWs()
                }
            }
        }        
    }
)