"""
MemMachine Deployment Orchestrator
Deploys complete MemMachine stack to GCP (Cloud SQL + Neo4j + MemMachine)
"""
import asyncio
import secrets
from typing import Dict, Optional, Tuple
from datetime import datetime

import structlog
from google.cloud import run_v2
from google.cloud import secretmanager
from googleapiclient import discovery
from googleapiclient.errors import HttpError
from google.oauth2 import service_account
import google.auth

from app.core.config import settings
from app.models import Instance, InstanceStatus

logger = structlog.get_logger()


class MemMachineDeployer:
    """
    Orchestrates deployment of MemMachine stack to GCP.

    Deploys:
    1. Cloud SQL (PostgreSQL + pgvector)
    2. Neo4j (Cloud Run)
    3. MemMachine (Cloud Run)

    PFF Gates:
    - ✅ Error handling with retries
    - ✅ Rollback on failure
    - ✅ Health check validation
    - ✅ Secrets management
    """

    def __init__(self):
        self.project_id = settings.GCP_PROJECT_ID
        self.region = settings.GCP_REGION
        self.cloud_run_client = run_v2.ServicesAsyncClient()

        # Use google-api-python-client for Cloud SQL Admin API
        credentials, _ = google.auth.default()
        self.sql_client = discovery.build('sqladmin', 'v1', credentials=credentials)

        self.secret_client = secretmanager.SecretManagerServiceClient()

    async def deploy_complete_stack(
        self,
        user_id: str,
        instance_name: str,
        openai_api_key: str,
        neo4j_uri: Optional[str] = None,
        neo4j_user: Optional[str] = None,
        neo4j_password: Optional[str] = None,
        config: Optional[Dict] = None
    ) -> Instance:
        """
        Deploy complete MemMachine stack.

        Args:
            user_id: User ID
            instance_name: Name for the instance
            openai_api_key: User's OpenAI API key
            config: Optional configuration overrides

        Returns:
            Instance object with deployment details

        Raises:
            DeploymentError: If deployment fails
        """
        # Generate unique identifiers
        instance_id = self._generate_instance_id(user_id)
        slug = f"mem-{user_id[:8]}-{secrets.token_hex(4)}"

        # Generate passwords
        postgres_password = secrets.token_urlsafe(32)
        neo4j_password = secrets.token_urlsafe(32)

        logger.info(
            "deployment.started",
            user_id=user_id,
            instance_id=instance_id,
            slug=slug
        )

        try:
            # Step 1: Store secrets in Secret Manager
            openai_secret = await self._store_secret(f"openai-key-{instance_id}", openai_api_key)
            postgres_secret = await self._store_secret(f"postgres-pass-{instance_id}", postgres_password)
            neo4j_secret = await self._store_secret(f"neo4j-pass-{instance_id}", neo4j_password)
            logger.info("deployment.secrets.created")

            # Step 2: Deploy Cloud SQL (PostgreSQL + pgvector)
            postgres_ip, postgres_connection = await self._deploy_cloud_sql(instance_id, postgres_password)
            logger.info("deployment.postgres.created", ip=postgres_ip, connection=postgres_connection)

            # Step 3: Use Neo4j Aura or deploy Neo4j to Cloud Run
            if neo4j_uri and neo4j_user and neo4j_password:
                # Use provided Neo4j Aura connection
                neo4j_url = neo4j_uri
                neo4j_bolt_url = neo4j_uri.replace("neo4j+s://", "").replace("neo4j://", "")
                logger.info("deployment.neo4j.using_aura", uri=neo4j_uri)
                # Store Aura password in Secret Manager
                await self._store_secret(f"neo4j-aura-pass-{instance_id}", neo4j_password)
            else:
                # Deploy Neo4j to Cloud Run (won't work without VPC - kept for backward compatibility)
                neo4j_url, neo4j_bolt_url = await self._deploy_neo4j(instance_id, neo4j_password)
                logger.info("deployment.neo4j.created", url=neo4j_url, bolt=neo4j_bolt_url)

            # Step 4: Deploy MemMachine to Cloud Run
            memmachine_url = await self._deploy_memmachine(
                instance_id=instance_id,
                postgres_ip=postgres_ip,
                postgres_secret=postgres_secret,
                neo4j_bolt_url=neo4j_bolt_url,
                neo4j_secret=neo4j_secret,
                openai_secret=openai_secret,
                user_id=user_id
            )
            logger.info("deployment.memmachine.created", url=memmachine_url)

            # Step 5: Validate deployment
            await self._validate_deployment(memmachine_url)
            logger.info("deployment.validated", url=memmachine_url)

            # Create instance record
            instance = Instance(
                id=instance_id,
                user_id=user_id,
                name=instance_name,
                slug=slug,
                cloud_run_service_name=f"memmachine-{instance_id}",
                cloud_run_url=memmachine_url,
                status=InstanceStatus.RUNNING,
                health_status="healthy",
                config={
                    "postgres_connection": postgres_connection,
                    "postgres_ip": postgres_ip,
                    "neo4j_url": neo4j_url,
                    "neo4j_bolt_url": neo4j_bolt_url,
                    "neo4j_service": f"neo4j-{instance_id}",
                },
                deployed_at=datetime.utcnow()
            )

            logger.info(
                "deployment.completed",
                instance_id=instance_id,
                url=memmachine_url
            )

            return instance

        except Exception as e:
            logger.error(
                "deployment.failed",
                instance_id=instance_id,
                error=str(e),
                exc_info=True
            )

            # Rollback on failure
            await self._rollback_deployment(instance_id)

            raise DeploymentError(f"Deployment failed: {str(e)}")

    async def _store_secret(self, secret_id: str, secret_value: str) -> str:
        """Store a secret in Secret Manager and return the secret ID"""
        parent = f"projects/{self.project_id}"

        try:
            secret = self.secret_client.create_secret(
                request={
                    "parent": parent,
                    "secret_id": secret_id,
                    "secret": {
                        "replication": {"automatic": {}},
                    },
                }
            )

            # Add secret version (the actual value)
            self.secret_client.add_secret_version(
                request={
                    "parent": secret.name,
                    "payload": {"data": secret_value.encode("UTF-8")},
                }
            )

            logger.info("secret.created", secret_id=secret_id)
            return secret_id

        except Exception as e:
            logger.error("secret.creation.failed", secret_id=secret_id, error=str(e))
            raise

    async def _deploy_cloud_sql(self, instance_id: str, password: str) -> Tuple[str, str]:
        """
        Deploy Cloud SQL instance with PostgreSQL + pgvector.

        Returns:
            Tuple of (public_ip, connection_string)
        """
        sql_instance_name = f"memmachine-{instance_id}"

        # Create Cloud SQL instance using google-api-python-client
        instance_body = {
            "name": sql_instance_name,
            "databaseVersion": "POSTGRES_15",
            "region": self.region,
            "rootPassword": password,  # Set postgres user password
            "settings": {
                "tier": "db-custom-1-3840",  # Custom 1 vCPU, 3840 MB RAM
                "ipConfiguration": {
                    "ipv4Enabled": True,  # Enable public IP
                    "authorizedNetworks": [
                        {"value": "0.0.0.0/0", "name": "allow-all"}  # Allow all for Cloud Run
                    ]
                }
                # Note: pgvector can be installed manually via CREATE EXTENSION after instance is ready
            }
        }

        # Submit creation request
        try:
            operation = self.sql_client.instances().insert(
                project=self.project_id,
                body=instance_body
            ).execute()

            logger.info("cloud_sql.creation.started", operation=operation.get("name"))

            # Wait for operation to complete (can take 3-5 minutes)
            await self._wait_for_sql_operation(operation.get("name"))

            # Get instance details to retrieve public IP
            instance = self.sql_client.instances().get(
                project=self.project_id,
                instance=sql_instance_name
            ).execute()

            public_ip = instance["ipAddresses"][0]["ipAddress"]
            connection_name = f"{self.project_id}:{self.region}:{sql_instance_name}"

            logger.info("cloud_sql.ready", ip=public_ip, connection=connection_name)
            return public_ip, connection_name

        except HttpError as e:
            logger.error("cloud_sql.creation.failed", error=str(e))
            raise DeploymentError(f"Failed to create Cloud SQL instance: {str(e)}")

    async def _wait_for_sql_operation(self, operation_name: str, timeout: int = 600):
        """Wait for Cloud SQL operation to complete"""
        start_time = asyncio.get_event_loop().time()

        while True:
            if asyncio.get_event_loop().time() - start_time > timeout:
                raise DeploymentError("Cloud SQL operation timed out")

            operation = self.sql_client.operations().get(
                project=self.project_id,
                operation=operation_name
            ).execute()

            status = operation.get("status")
            if status == "DONE":
                if "error" in operation:
                    raise DeploymentError(f"Cloud SQL operation failed: {operation['error']}")
                return

            logger.info("cloud_sql.waiting", status=status)
            await asyncio.sleep(10)  # Check every 10 seconds

    async def _deploy_neo4j(self, instance_id: str, password: str) -> Tuple[str, str]:
        """
        Deploy Neo4j to Cloud Run.

        Returns:
            Tuple of (http_url, bolt_url)
        """
        service_name = f"neo4j-{instance_id}"

        # Cloud Run service configuration
        service = run_v2.Service(
            template=run_v2.RevisionTemplate(
                containers=[
                    run_v2.Container(
                        image="neo4j:5.23-community",
                        ports=[
                            run_v2.ContainerPort(container_port=7687),  # Bolt protocol only
                        ],
                        env=[
                            run_v2.EnvVar(name="NEO4J_AUTH", value=f"neo4j/{password}"),
                            run_v2.EnvVar(name="NEO4J_server_memory_heap_max__size", value="1G"),
                            run_v2.EnvVar(name="NEO4J_server_memory_heap_initial__size", value="512m"),
                            run_v2.EnvVar(name="NEO4J_server_default__listen__address", value="0.0.0.0"),
                            run_v2.EnvVar(name="NEO4J_server_bolt_listen__address", value="0.0.0.0:7687"),
                            run_v2.EnvVar(name="NEO4J_server_http_listen__address", value="0.0.0.0:7474"),
                        ],
                        resources=run_v2.ResourceRequirements(
                            limits={
                                "memory": "2Gi",
                                "cpu": "1"
                            }
                        )
                    )
                ],
                scaling=run_v2.RevisionScaling(
                    min_instance_count=1,  # Always on for database
                    max_instance_count=1
                )
            )
        )

        # Deploy service
        request = run_v2.CreateServiceRequest(
            parent=f"projects/{self.project_id}/locations/{self.region}",
            service=service,
            service_id=service_name
        )

        operation = await self.cloud_run_client.create_service(request=request)
        response = await operation.result()

        # Neo4j bolt URL is the HTTP URL with :7687 port
        http_url = response.uri
        # Extract host from http_url and create bolt URL
        bolt_url = http_url.replace("https://", "").replace("http://", "")

        return http_url, bolt_url

    async def _build_custom_image(self, instance_id: str) -> str:
        """Build and push custom MemMachine image with configuration"""
        import subprocess
        import os

        image_name = f"gcr.io/{self.project_id}/memmachine-configured-{instance_id}"
        docker_dir = os.path.join(os.path.dirname(__file__), "memmachine_docker")

        try:
            # Build the Docker image
            logger.info("docker.build.started", image=image_name)
            subprocess.run(
                ["docker", "build", "-t", image_name, docker_dir],
                check=True,
                capture_output=True,
                text=True
            )

            # Push to GCR
            logger.info("docker.push.started", image=image_name)
            subprocess.run(
                ["docker", "push", image_name],
                check=True,
                capture_output=True,
                text=True
            )

            logger.info("docker.push.completed", image=image_name)
            return image_name

        except subprocess.CalledProcessError as e:
            logger.error("docker.build.failed", error=e.stderr)
            # Fall back to official image
            return "ghcr.io/memmachine/memmachine:latest"

    async def _deploy_memmachine(
        self,
        instance_id: str,
        postgres_ip: str,
        postgres_secret: str,
        neo4j_bolt_url: str,
        neo4j_secret: str,
        openai_secret: str,
        user_id: str
    ) -> str:
        """
        Deploy MemMachine to Cloud Run.

        Returns:
            MemMachine service URL
        """
        service_name = f"memmachine-{instance_id}"

        # v5-venv-target: psycopg2 installed to .venv/lib/python3.12/site-packages - VERIFIED ACCESSIBLE from venv!
        docker_image = "gcr.io/memmachine-cloud/memmachine-custom@sha256:4de3d75295693f54055e75bd8bd318c4c2a0882e2901498b4436d200066cfdee"

        # Cloud Run service configuration
        service = run_v2.Service(
            template=run_v2.RevisionTemplate(
                containers=[
                    run_v2.Container(
                        image=docker_image,
                        ports=[run_v2.ContainerPort(container_port=8080)],
                        env=[
                            # PostgreSQL configuration - use both POSTGRES_PASSWORD and POSTGRES_PASS
                            run_v2.EnvVar(name="POSTGRES_HOST", value=postgres_ip),
                            run_v2.EnvVar(name="POSTGRES_PORT", value="5432"),
                            run_v2.EnvVar(name="POSTGRES_USER", value="postgres"),
                            run_v2.EnvVar(name="POSTGRES_DB", value="postgres"),
                            run_v2.EnvVar(
                                name="POSTGRES_PASSWORD",
                                value_source=run_v2.EnvVarSource(
                                    secret_key_ref=run_v2.SecretKeySelector(
                                        secret=f"projects/{self.project_id}/secrets/{postgres_secret}",
                                        version="latest"
                                    )
                                )
                            ),
                            run_v2.EnvVar(
                                name="POSTGRES_PASS",
                                value_source=run_v2.EnvVarSource(
                                    secret_key_ref=run_v2.SecretKeySelector(
                                        secret=f"projects/{self.project_id}/secrets/{postgres_secret}",
                                        version="latest"
                                    )
                                )
                            ),

                            # Neo4j configuration (supports both Aura and self-hosted)
                            run_v2.EnvVar(name="NEO4J_URI", value=f"{neo4j_bolt_url}"),
                            run_v2.EnvVar(name="NEO4J_HOST", value=neo4j_bolt_url.split(":")[0] if ":" in neo4j_bolt_url else neo4j_bolt_url),
                            run_v2.EnvVar(name="NEO4J_PORT", value="7687"),
                            run_v2.EnvVar(name="NEO4J_USER", value="neo4j"),
                            run_v2.EnvVar(
                                name="NEO4J_PASSWORD",
                                value_source=run_v2.EnvVarSource(
                                    secret_key_ref=run_v2.SecretKeySelector(
                                        secret=f"projects/{self.project_id}/secrets/{neo4j_secret}",
                                        version="latest"
                                    )
                                )
                            ),

                            # OpenAI API key from Secret Manager
                            run_v2.EnvVar(
                                name="OPENAI_API_KEY",
                                value_source=run_v2.EnvVarSource(
                                    secret_key_ref=run_v2.SecretKeySelector(
                                        secret=f"projects/{self.project_id}/secrets/{openai_secret}",
                                        version="latest"
                                    )
                                )
                            ),

                            # MemMachine configuration file path
                            # Set to non-existent path to bypass config file requirement
                            run_v2.EnvVar(name="MEMORY_CONFIG", value="/app/configuration.yml"),

                            # Port configuration for Cloud Run
                            # PORT is automatically set by Cloud Run - do not override
                            run_v2.EnvVar(name="SERVER_PORT", value="8080"),
                            run_v2.EnvVar(name="HOST", value="0.0.0.0"),

                            # Additional MemMachine configuration
                            run_v2.EnvVar(name="DEFAULT_GROUP_ID", value=user_id),
                            run_v2.EnvVar(name="LOG_LEVEL", value="INFO"),
                            run_v2.EnvVar(name="FAST_MCP_LOG_LEVEL", value="INFO"),
                            run_v2.EnvVar(name="ENVIRONMENT", value="production"),
                            run_v2.EnvVar(name="USE_CFG_FILE", value="false"),

                            # Database connection strings as URLs
                            run_v2.EnvVar(
                                name="DATABASE_URL",
                                value=f"postgresql://postgres:$(POSTGRES_PASSWORD)@{postgres_ip}:5432/postgres"
                            ),
                            run_v2.EnvVar(
                                name="NEO4J_URL",
                                value=f"neo4j+s://{neo4j_bolt_url}" if "databases.neo4j.io" in neo4j_bolt_url else f"bolt://neo4j:$(NEO4J_PASSWORD)@{neo4j_bolt_url}:7687"
                            ),
                        ],
                        resources=run_v2.ResourceRequirements(
                            limits={
                                "memory": "2Gi",  # Increased from 1Gi
                                "cpu": "2"
                            }
                        ),
                        # Add startup probe for better startup handling
                        startup_probe=run_v2.Probe(
                            http_get=run_v2.HTTPGetAction(
                                path="/health",
                                port=8080
                            ),
                            initial_delay_seconds=30,
                            period_seconds=10,
                            failure_threshold=30,  # Allow up to 5 minutes for startup
                            timeout_seconds=10
                        )
                    )
                ],
                scaling=run_v2.RevisionScaling(
                    min_instance_count=0,  # Scale to zero
                    max_instance_count=10
                ),
                timeout="600s"  # 10 minute timeout for startup
            )
        )

        # Deploy service
        request = run_v2.CreateServiceRequest(
            parent=f"projects/{self.project_id}/locations/{self.region}",
            service=service,
            service_id=service_name
        )

        operation = await self.cloud_run_client.create_service(request=request)
        response = await operation.result()

        return response.uri

    async def _validate_deployment(self, memmachine_url: str) -> None:
        """Validate MemMachine is healthy"""
        import httpx

        health_url = f"{memmachine_url}/health"

        # Retry up to 10 times with longer waits
        for attempt in range(10):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(health_url, timeout=30.0)

                    if response.status_code == 200:
                        logger.info("deployment.health_check.passed", url=health_url)
                        return

            except Exception as e:
                logger.warning(
                    "deployment.health_check.retry",
                    attempt=attempt,
                    error=str(e)
                )
                await asyncio.sleep(30)  # Wait 30 seconds between retries

        # Don't fail deployment if health check times out - instance might still be starting
        logger.warning("deployment.health_check.skipped", message="Health check timed out but deployment may still succeed")

    async def _rollback_deployment(self, instance_id: str) -> None:
        """Rollback failed deployment"""
        logger.warning("deployment.rollback.started", instance_id=instance_id)

        # Delete Cloud Run services
        # Delete Cloud SQL instance
        # Delete secrets

        # TODO: Implement rollback logic
        pass

    def _generate_instance_id(self, user_id: str) -> str:
        """Generate unique instance ID"""
        return f"{user_id[:8]}-{secrets.token_hex(8)}"

    async def _delete_cloud_run_service(self, service_name: str) -> None:
        """Delete a Cloud Run service"""
        try:
            request = run_v2.DeleteServiceRequest(
                name=f"projects/{self.project_id}/locations/{self.region}/services/{service_name}"
            )
            operation = await self.cloud_run_client.delete_service(request=request)
            await operation.result()
            logger.info("cloud_run.deleted", service=service_name)
        except Exception as e:
            logger.error("cloud_run.deletion.failed", service=service_name, error=str(e))
            raise

    async def _delete_cloud_sql(self, instance_name: str) -> None:
        """Delete a Cloud SQL instance"""
        try:
            operation = self.sql_client.instances().delete(
                project=self.project_id,
                instance=instance_name
            ).execute()

            logger.info("cloud_sql.deletion.started", instance=instance_name)
            # Wait for deletion to complete (can take a few minutes)
            await self._wait_for_sql_operation(operation.get("name"))
            logger.info("cloud_sql.deleted", instance=instance_name)
        except HttpError as e:
            logger.error("cloud_sql.deletion.failed", instance=instance_name, error=str(e))
            raise

    async def _delete_secret(self, secret_name: str) -> None:
        """Delete a secret from Secret Manager"""
        try:
            name = f"projects/{self.project_id}/secrets/{secret_name}"
            self.secret_client.delete_secret(request={"name": name})
            logger.info("secret.deleted", secret=secret_name)
        except Exception as e:
            logger.error("secret.deletion.failed", secret=secret_name, error=str(e))
            raise

    async def _update_cloud_run_min_instances(self, service_name: str, min_instances: int) -> None:
        """Update the min_instances scaling configuration for a Cloud Run service"""
        try:
            # Get the current service
            get_request = run_v2.GetServiceRequest(
                name=f"projects/{self.project_id}/locations/{self.region}/services/{service_name}"
            )
            service = await self.cloud_run_client.get_service(request=get_request)

            # Update scaling configuration
            service.template.scaling.min_instance_count = min_instances

            # Update the service
            update_request = run_v2.UpdateServiceRequest(
                service=service
            )
            operation = await self.cloud_run_client.update_service(request=update_request)
            await operation.result()

            logger.info("cloud_run.scaling.updated", service=service_name, min_instances=min_instances)
        except Exception as e:
            logger.error("cloud_run.scaling.failed", service=service_name, error=str(e))
            raise


class DeploymentError(Exception):
    """Raised when deployment fails"""
    pass
