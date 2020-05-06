node("master") {
    try {
        stage("checkout scm") {
            checkout scm
        }

        stage("run dos2unix") {
            sh "find . -type f -print0 | xargs -0 dos2unix"
        }

        stage("Remove name from licence") {
            sh "sed -i 's/Philip Woldhek/Crucified Midget/g' MEGAabuse.py"
        }

        stage("Pylint") {
            sh 'pylint --disable=W1202 --output-format=parseable --reports=no module > pylint.log || echo "pylint exited with $?"'

            step([
                    $class                     : 'WarningsPublisher',
                    parserConfigurations       : [[
                                                          parserName: 'PYLint',
                                                          pattern   : 'pylint.log'
                                                 ]],
                    unstableTotalAll           : '0',   
                    usePreviousBuildAsReference: true
            ])
        }

        // stage("Create packages") {
        //     parallel(
        //         windows: {
        //             sh "mkdir -p windows/binaries"
        //             sh "cp -r binaries/megacmd_windows windows/binaries/"
        //             sh "cp -r binaries/megatools_win windows/binaries/"
        //             sh "cp requirements.txt MEGAabuse.py guerrillamail.py windows/"
        //         },
        //         linux: {
        //             sh "mkdir -p linux/binaries"    
        //             sh "cp -r binaries/megacmd_linux linux/binaries/"
        //             sh "cp -r binaries/megatools_linux linux/binaries/"
        //             sh "cp requirements.txt MEGAabuse.py guerrillamail.py linux/"
        //         },
        //         mac: {
        //             sh "mkdir -p mac/binaries"
        //             sh "cp -r binaries/megacmd_mac mac/binaries/"
        //             sh "cp -r binaries/megatools_mac mac/binaries/"
        //             sh "cp requirements.txt MEGAabuse.py guerrillamail.py mac/"
        //         }
        //     )
        // }
    }

    catch(err){
        println(err.toString())
        error(err.getMessage())
        currentBuild.result = 'FAILED'
        exception_msg = err.getMessage();
    }

    finally {
        stage('Clean Workspace') {
            // cleanWs()
        }
    }
}