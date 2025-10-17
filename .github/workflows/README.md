# GitHub Actions - Deploy Infrastructure

This directory contains GitHub Actions workflows to automate the deployment of AWS ECS infrastructure.

## Setup

### 1. Configure GitHub Secrets

In your GitHub repository, go to **Settings > Secrets and variables > Actions** and add the following secrets:

- `AWS_ACCESS_KEY_ID`: Your AWS Access Key ID
- `AWS_SECRET_ACCESS_KEY`: Your AWS Secret Access Key

⚠️ **Important**: Never put these credentials directly in the code. Only in GitHub Secrets.

### 2. Create Secrets in AWS Secrets Manager

Before running the deployment, make sure to create the necessary secrets:

```bash
# LiveKit URL
aws secretsmanager create-secret \
  --name ecs/agent-example/livekit-url \
  --region us-east-1 \
  --secret-string "wss://your-url.livekit.cloud"

# LiveKit API Key
aws secretsmanager create-secret \
  --name ecs/agent-example/livekit-api-key \
  --region us-east-1 \
  --secret-string "your-api-key"

# LiveKit API Secret
aws secretsmanager create-secret \
  --name ecs/agent-example/livekit-api-secret \
  --region us-east-1 \
  --secret-string "your-api-secret"

# OpenAI API Key
aws secretsmanager create-secret \
  --name ecs/agent-example/openai-api-key \
  --region us-east-1 \
  --secret-string "your-openai-api-key"

# Serper API Key
aws secretsmanager create-secret \
  --name ecs/agent-example/serper-api-key \
  --region us-east-1 \
  --secret-string "your-serper-api-key"
```

Update the `cloudformation.yaml` file with the ARNs of these secrets (replace `<unique-id>` with the actual ID).

To get the ARNs:

```bash
aws secretsmanager describe-secret --secret-id ecs/agent-example/livekit-url
aws secretsmanager describe-secret --secret-id ecs/agent-example/livekit-api-key
aws secretsmanager describe-secret --secret-id ecs/agent-example/livekit-api-secret
aws secretsmanager describe-secret --secret-id ecs/agent-example/openai-api-key
aws secretsmanager describe-secret --secret-id ecs/agent-example/serper-api-key
```

### 3. Configure environment variables (optional)

You can modify the environment variables in the `deploy-infra.yaml` file:

- `AWS_REGION`: AWS Region (default: `us-east-1`)
- `STACK_NAME`: CloudFormation stack name (default: `agents-stack`)
- `ECR_REPOSITORY`: ECR repository name (default: `agent-example`)

## Usage

### Automatic deployment

The workflow runs automatically when:

- You push to the `main` branch with changes in `backend/` or in the workflow

### Manual deployment

1. Go to **Actions** in GitHub
2. Select the **Deploy Infrastructure to AWS ECS** workflow
3. Click on **Run workflow**
4. (Optional) Specify a custom version for the Docker image
5. Click on **Run workflow**

## Versioning

The workflow automatically generates version tags with the format:

```
YYYYMMDD-HHMMSS-<git-sha>
```

For example: `20231025-143022-abc1234`

Each image is also tagged as `latest`.

## Monitoring

After deployment, you can monitor your application:

### View CloudWatch logs:

```bash
aws logs tail /ecs/agent-example --follow
```

### View service status:

```bash
aws ecs describe-services \
  --cluster AgentCluster \
  --services AgentExampleService \
  --region us-east-1
```

### View running tasks:

```bash
aws ecs list-tasks \
  --cluster AgentCluster \
  --service-name AgentExampleService \
  --region us-east-1
```

## Troubleshooting

### Error: "Stack does not exist"

If this is the first time you run the workflow, the stack will be created automatically. Make sure that:

1. AWS Secrets Manager secrets exist
2. The ARNs in `cloudformation.yaml` are correct
3. The `DesiredCount` is set to `0` for the first deployment

### Error: "No changes to deploy"

This is normal when there are no changes to the infrastructure. The workflow will continue and force a new deployment of the Docker image.

### Permission errors

Verify that your AWS IAM user has the necessary permissions for:

- ECR (Amazon Elastic Container Registry)
- ECS (Amazon Elastic Container Service)
- CloudFormation
- IAM (to create roles)
- EC2 (for VPC, subnets, security groups)
- CloudWatch Logs

## Scaling the service

To change the number of running instances, modify `DesiredCount` in the `cloudformation.yaml` file and commit. The workflow will detect the change and automatically update the stack.

```yaml
AgentExampleService:
  Type: AWS::ECS::Service
  Properties:
    # ...
    DesiredCount: 1 # Change this value
```

## Rollback

To rollback to a previous version:

1. Run the workflow manually
2. Specify the previous version in the `version` input
3. The workflow will deploy that specific version

You can also rollback manually:

```bash
# List image versions
aws ecr list-images --repository-name agent-example --region us-east-1

# Update CloudFormation with the desired version
# Edit cloudformation.yaml and run:
aws cloudformation update-stack \
  --stack-name agents-stack \
  --template-body file://cloudformation.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1
```
