# GitHub Actions - Deploy Infrastructure

Este directorio contiene workflows de GitHub Actions para automatizar el deploy de la infraestructura AWS ECS.

## Configuración

### 1. Configurar GitHub Secrets

En tu repositorio de GitHub, ve a **Settings > Secrets and variables > Actions** y agrega los siguientes secrets:

- `AWS_ACCESS_KEY_ID`: Tu AWS Access Key ID
- `AWS_SECRET_ACCESS_KEY`: Tu AWS Secret Access Key

⚠️ **Importante**: Nunca pongas estas credenciales directamente en el código. Solo en GitHub Secrets.

### 2. Crear Secrets en AWS Secrets Manager

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

### 3. Configurar variables de entorno (opcional)

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

Verifica que tu usuario de AWS IAM tiene los permisos necesarios para:

- ECR (Amazon Elastic Container Registry)
- ECS (Amazon Elastic Container Service)
- CloudFormation
- IAM (para crear roles)
- EC2 (para VPC, subnets, security groups)
- CloudWatch Logs

## Escalar el servicio

Para cambiar el número de instancias en ejecución, modifica `DesiredCount` en el archivo `cloudformation.yaml` y haz commit. El workflow detectará el cambio y actualizará el stack automáticamente.

```yaml
AgentExampleService:
  Type: AWS::ECS::Service
  Properties:
    # ...
    DesiredCount: 1 # Cambia este valor
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
