# AWS Lightsail Container Service deployment

This guide deploys the Docker image as one public Streamlit container on the smallest Lightsail Container Service configuration. Run commands from the repository root. The service can incur AWS charges until deleted.

## Prerequisites and safe access check

Install Docker, AWS CLI v2, and the AWS Lightsail Control plugin (`lightsailctl`). AWS's current setup guide is available in the [Lightsail documentation](https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-install-software.html). Configure credentials using your organisation's approved method (for example, `aws configure sso` and `aws sso login`, or `aws configure`). Never put credentials in this repository, the Docker image, command arguments, or documentation.

The following commands report identity and region without printing secret credentials:

```bash
aws --version
lightsailctl --version
aws sts get-caller-identity
aws configure get region
docker version
```

The identity needs permission for the Lightsail container-service operations used below. If the region command is blank, choose a Lightsail-supported region and configure it, for example:

```bash
aws configure set region eu-west-1
```

Set reusable names. Keep these exact values if following the rest of the guide:

```bash
export AWS_REGION="$(aws configure get region)"
export LIGHTSAIL_SERVICE="evaluation-data-inspector"
export CONTAINER_NAME="app"
```

Confirm that all three values are non-empty before proceeding.

### Status in the final QA environment

- `docker` was not installed or was not available in `PATH` (`command not found`, status 127).
- `aws` was not installed or was not available in `PATH` (`command not found`, status 127).
- Therefore a Docker image/container could not be built or run here, and AWS identity, configured region, image push, deployment, and public HTTPS checks could not be performed.
- User intervention required: install/start Docker, install AWS CLI v2 and `lightsailctl`, authenticate the CLI, select a region, then run the verified sequence below. Do not share credentials in chat or commit them.

## 1. Build and verify locally

```bash
docker build --platform linux/amd64 -t evaluation-data-inspector:latest .
docker run --rm -d -p 8501:8501 --name evaluation-data-inspector evaluation-data-inspector:latest
curl --fail --retry 12 --retry-delay 2 http://localhost:8501/_stcore/health
docker stop evaluation-data-inspector
```

If your deployment target supports ARM64 and you intentionally prefer it, adjust the platform. `linux/amd64` is the conservative portable default.

## 2. Create the service

First ensure a service with the chosen name does not already belong to someone else:

```bash
aws lightsail get-container-services --service-name "$LIGHTSAIL_SERVICE" --region "$AWS_REGION"
```

If AWS returns `NotFoundException`, create the project's service:

```bash
aws lightsail create-container-service \
  --service-name "$LIGHTSAIL_SERVICE" \
  --power nano \
  --scale 1 \
  --region "$AWS_REGION"
```

Wait until its state is `READY`:

```bash
aws lightsail get-container-services \
  --service-name "$LIGHTSAIL_SERVICE" \
  --region "$AWS_REGION" \
  --query 'containerServices[0].state' \
  --output text
```

Repeat the read-only status command after a short interval until it reports `READY`.

## 3. Push the image

Lightsail's push helper uploads the local image to the service's private image store:

```bash
aws lightsail push-container-image \
  --service-name "$LIGHTSAIL_SERVICE" \
  --label evaluation-data-inspector \
  --image evaluation-data-inspector:latest \
  --region "$AWS_REGION"
```

Resolve the exact uploaded image identifier rather than assuming its version number:

```bash
export LIGHTSAIL_IMAGE="$(aws lightsail get-container-images \
  --service-name "$LIGHTSAIL_SERVICE" \
  --region "$AWS_REGION" \
  --query 'sort_by(containerImages,&createdAt)[-1].image' \
  --output text)"
```

It should resemble `:evaluation-data-inspector.evaluation-data-inspector.N` and must not be empty.

## 4. Create the public deployment

The app listens on port 8501. The endpoint uses Streamlit's lightweight health route.

```bash
aws lightsail create-container-service-deployment \
  --service-name "$LIGHTSAIL_SERVICE" \
  --region "$AWS_REGION" \
  --containers "{\"$CONTAINER_NAME\":{\"image\":\"$LIGHTSAIL_IMAGE\",\"ports\":{\"8501\":\"HTTP\"},\"environment\":{\"STREAMLIT_SERVER_HEADLESS\":\"true\",\"STREAMLIT_BROWSER_GATHER_USAGE_STATS\":\"false\"}}}" \
  --public-endpoint "{\"containerName\":\"$CONTAINER_NAME\",\"containerPort\":8501,\"healthCheck\":{\"path\":\"/_stcore/health\",\"successCodes\":\"200-399\",\"intervalSeconds\":10,\"timeoutSeconds\":5,\"healthyThreshold\":2,\"unhealthyThreshold\":2}}"
```

Monitor the deployment without changing any resources:

```bash
aws lightsail get-container-services \
  --service-name "$LIGHTSAIL_SERVICE" \
  --region "$AWS_REGION" \
  --query 'containerServices[0].{state:state,deployment:currentDeployment.state,url:url}'
```

When the deployment state is `ACTIVE`, capture and test its HTTPS URL:

```bash
export APP_URL="$(aws lightsail get-container-services \
  --service-name "$LIGHTSAIL_SERVICE" \
  --region "$AWS_REGION" \
  --query 'containerServices[0].url' \
  --output text)"

curl --fail --retry 12 --retry-delay 5 "$APP_URL/_stcore/health"
```

Open `$APP_URL` in a browser and exercise the synthetic sample, one valid upload, and one malformed upload.

## Updates and rollback visibility

For an update, rebuild, run the same `push-container-image` command, resolve the new image identifier, and create a new deployment. Lightsail retains deployment/image metadata that can help identify a prior known-good image. Inspect it with:

```bash
aws lightsail get-container-service-deployments \
  --service-name "$LIGHTSAIL_SERVICE" \
  --region "$AWS_REGION"
```

Do not delete old images until the new deployment is verified.

## Logs and troubleshooting

List container logs for the current deployment:

```bash
aws lightsail get-container-log \
  --service-name "$LIGHTSAIL_SERVICE" \
  --container-name "$CONTAINER_NAME" \
  --region "$AWS_REGION"
```

Common causes of a failed deployment are an image built for the wrong CPU architecture, port 8501 not exposed in the deployment, a failed health check, or insufficient IAM permission.

## Cleanup

Only delete the service if it was created specifically for this project and you no longer want the public app:

```bash
aws lightsail delete-container-service \
  --service-name "$LIGHTSAIL_SERVICE" \
  --region "$AWS_REGION"
```

Deletion is destructive and stops billing for that container service after AWS finishes removing it. It does not affect unrelated Lightsail resources.
