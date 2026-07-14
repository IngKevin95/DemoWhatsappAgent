# ci-cd-pipeline Specification

## Purpose
TBD - created by archiving change ep-005-mini. Update Purpose after archive.
## Requirements
### Requirement: Test Stage (CI)
The system SHALL run automated tests on every push to a feature branch, preventing merge if tests fail or coverage drops below threshold.

#### Scenario: Dependency installation
- **WHEN** GitHub Actions trigger on push to feature branch
- **THEN** workflow checks out code and runs `pip install -r requirements.txt`

#### Scenario: Test execution
- **WHEN** dependencies are installed
- **THEN** workflow runs `pytest -v --cov` and reports coverage percentage

#### Scenario: Coverage gate
- **WHEN** tests complete
- **THEN** if coverage < 70%, workflow fails and blocks merge

#### Scenario: Security scanning
- **WHEN** tests pass
- **THEN** workflow runs `bandit` (SAST) and reports findings; critical findings block merge

#### Scenario: All checks must pass
- **WHEN** test stage completes
- **THEN** workflow proceeds to build stage only if all checks (tests, coverage, security) pass

### Requirement: Build Stage (Image Creation)
The system SHALL build and tag Docker image only if test stage passes.

#### Scenario: Image build
- **WHEN** test stage passes
- **THEN** workflow runs `docker build -t demobot:latest .` (plus git commit hash tag)

#### Scenario: Image tag includes commit hash
- **WHEN** image is built
- **THEN** image is tagged as both `demobot:latest` and `demobot:<commit-hash>`

### Requirement: Push Stage (Registry)
The system SHALL push built image to a Docker registry (Docker Hub or AWS ECR).

#### Scenario: Push to registry
- **WHEN** image build completes
- **THEN** workflow authenticates to registry (via GitHub Secrets) and pushes both tags

#### Scenario: Registry credentials
- **WHEN** workflow runs
- **THEN** uses GitHub repository secrets (DOCKER_USERNAME, DOCKER_PASSWORD or AWS credentials) injected as environment variables

### Requirement: Deploy Stage (Release)
The system SHALL trigger deployment to staging/production only from main branch.

#### Scenario: Deploy on main push
- **WHEN** push to main branch occurs and all tests pass
- **THEN** workflow triggers deployment of latest image to production environment

#### Scenario: Deployment workflow
- **WHEN** deploy stage starts
- **THEN** pulls latest image from registry, starts new container with environment variables, verifies health check passes, marks deployment successful

#### Scenario: No deploy from feature branch
- **WHEN** push to feature branch (not main) occurs
- **THEN** test/build/push stages run, but deploy stage is skipped

### Requirement: Workflow File
The system SHALL provide .github/workflows/deploy.yml defining the entire pipeline.

#### Scenario: Workflow is version controlled
- **WHEN** repository is cloned
- **THEN** `.github/workflows/deploy.yml` exists and is tracked in git

