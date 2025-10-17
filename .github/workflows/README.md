# GitHub Actions - Deploy Infrastructure

Este directorio contiene workflows de GitHub Actions para automatizar el deploy de la infraestructura AWS ECS.

## Configuración

### 1. Configurar AWS OIDC (Recomendado)

Para usar GitHub Actions con AWS de forma segura, configura OpenID Connect (OIDC) en lugar de usar credenciales de larga duración:

#### Crear el Identity Provider en AWS:

```bash
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
```

#### Crear el IAM Role:

Crea un archivo `trust-policy.json`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::<AWS_ACCOUNT_ID>:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:<GITHUB_ORG>/<REPO_NAME>:*"
        }
      }
    }
  ]
}
```

Reemplaza `<AWS_ACCOUNT_ID>`, `<GITHUB_ORG>`, y `<REPO_NAME>` con tus valores.

Crea el role:

```bash
aws iam create-role \
  --role-name GitHubActionsDeployRole \
  --assume-role-policy-document file://trust-policy.json
```

#### Agregar permisos al role:

```bash
# Permisos para ECR
aws iam attach-role-policy \
  --role-name GitHubActionsDeployRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser

# Permisos para ECS
aws iam attach-role-policy \
  --role-name GitHubActionsDeployRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonECS_FullAccess

# Permisos para CloudFormation
aws iam attach-role-policy \
  --role-name GitHubActionsDeployRole \
  --policy-arn arn:aws:iam::aws:policy/AWSCloudFormationFullAccess

# Permisos adicionales para IAM (necesarios para CloudFormation)
aws iam put-role-policy \
  --role-name GitHubActionsDeployRole \
  --policy-name AdditionalPermissions \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "iam:CreateRole",
          "iam:DeleteRole",
          "iam:GetRole",
          "iam:PassRole",
          "iam:AttachRolePolicy",
          "iam:DetachRolePolicy",
          "iam:PutRolePolicy",
          "iam:DeleteRolePolicy",
          "ec2:*",
          "logs:*"
        ],
        "Resource": "*"
      }
    ]
  }'
```

### 2. Configurar GitHub Secrets

En tu repositorio de GitHub, ve a **Settings > Secrets and variables > Actions** y agrega:

- `AWS_ROLE_ARN`: ARN del role creado anteriormente (ej: `arn:aws:iam::<ACCOUNT_ID>:role/GitHubActionsDeployRole`)

### 3. Crear Secrets en AWS Secrets Manager

Antes de ejecutar el deploy, asegúrate de crear los secrets necesarios:

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
```

Actualiza el archivo `cloudformation.yaml` con los ARNs de estos secrets (reemplaza `<unique-id>` con el ID real).

Para obtener los ARNs:

```bash
aws secretsmanager describe-secret --secret-id ecs/agent-example/livekit-url
aws secretsmanager describe-secret --secret-id ecs/agent-example/livekit-api-key
aws secretsmanager describe-secret --secret-id ecs/agent-example/livekit-api-secret
```

### 4. Configurar variables de entorno (opcional)

Puedes modificar las variables de entorno en el archivo `deploy-infra.yaml`:

- `AWS_REGION`: Región de AWS (por defecto: `us-east-1`)
- `STACK_NAME`: Nombre del stack de CloudFormation (por defecto: `agents-stack`)
- `ECR_REPOSITORY`: Nombre del repositorio ECR (por defecto: `agent-example`)

## Uso

### Deploy automático

El workflow se ejecuta automáticamente cuando:
- Se hace push a la rama `main` con cambios en `backend/` o en el workflow

### Deploy manual

1. Ve a **Actions** en GitHub
2. Selecciona el workflow **Deploy Infrastructure to AWS ECS**
3. Click en **Run workflow**
4. (Opcional) Especifica una versión personalizada para la imagen Docker
5. Click en **Run workflow**

## Versionamiento

El workflow genera automáticamente tags de versión con el formato:
```
YYYYMMDD-HHMMSS-<git-sha>
```

Por ejemplo: `20231025-143022-abc1234`

Cada imagen también se tagea como `latest`.

## Monitoreo

Después del deploy, puedes monitorear tu aplicación:

### Ver logs en CloudWatch:

```bash
aws logs tail /ecs/agent-example --follow
```

### Ver estado del servicio:

```bash
aws ecs describe-services \
  --cluster AgentCluster \
  --services AgentExampleService \
  --region us-east-1
```

### Ver tareas en ejecución:

```bash
aws ecs list-tasks \
  --cluster AgentCluster \
  --service-name AgentExampleService \
  --region us-east-1
```

## Troubleshooting

### Error: "Stack does not exist"

Si es la primera vez que ejecutas el workflow, el stack será creado automáticamente. Asegúrate de que:
1. Los secrets de AWS Secrets Manager existen
2. Los ARNs en `cloudformation.yaml` son correctos
3. El `DesiredCount` está en `0` para el primer deploy

### Error: "No changes to deploy"

Esto es normal cuando no hay cambios en la infraestructura. El workflow continuará y forzará un nuevo deploy de la imagen Docker.

### Error de permisos

Verifica que el role de IAM tiene todos los permisos necesarios mencionados en la sección de configuración.

## Escalar el servicio

Para cambiar el número de instancias en ejecución, modifica `DesiredCount` en el archivo `cloudformation.yaml` y haz commit. El workflow detectará el cambio y actualizará el stack automáticamente.

```yaml
AgentExampleService:
  Type: AWS::ECS::Service
  Properties:
    # ...
    DesiredCount: 1  # Cambia este valor
```

## Rollback

Para hacer rollback a una versión anterior:

1. Ejecuta el workflow manualmente
2. Especifica la versión anterior en el input `version`
3. El workflow deployará esa versión específica

También puedes hacer rollback manual:

```bash
# Listar versiones de imágenes
aws ecr list-images --repository-name agent-example --region us-east-1

# Actualizar el CloudFormation con la versión deseada
# Edita cloudformation.yaml y ejecuta:
aws cloudformation update-stack \
  --stack-name agents-stack \
  --template-body file://cloudformation.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1
```

