def call(Map config = [:]) {
  def mode = config.mode ?: (env.TAG_NAME ? 'publish' : 'preview')
  def gate = config.gate ?: 'warn'
  def language = config.language ?: 'en'
  if (!config.sbom) { error('conformeshCra requires sbom') }
  withCredentials([string(credentialsId: config.credentialsId ?: 'conformesh-pipeline-token', variable: 'CONFORMESH_PIPELINE_TOKEN')]) {
    def release = mode == 'publish' ? "--release-key '${config.releaseKey}' --version '${config.version}'" : ''
    sh "docker run --rm -v \"${env.WORKSPACE}:/work\" -e CONFORMESH_PIPELINE_TOKEN -e JENKINS_URL -e BUILD_URL -e BUILD_TAG -e BUILD_NUMBER -e GIT_URL -e GIT_COMMIT -e BRANCH_NAME ghcr.io/conformesh/conformesh-pipeline-cli:1.0.2 ${mode} --sbom '${config.sbom}' --gate '${gate}' --language '${language}' --output conformesh-output ${release}"
  }
  archiveArtifacts artifacts: 'conformesh-output/**', fingerprint: true
}
