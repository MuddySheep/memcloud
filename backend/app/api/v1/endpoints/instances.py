"""
Instance Management API Endpoints
Handles MemMachine instance deployments
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.db.database import get_db_session
from app.models import Instance, InstanceStatus
import structlog

# Make deployer optional for local development
try:
    from app.services.memmachine_deployer import MemMachineDeployer, DeploymentError
    DEPLOYER_AVAILABLE = True
except ImportError as e:
    DEPLOYER_AVAILABLE = False
    DeploymentError = Exception
    logger = structlog.get_logger()
    logger.warning("memmachine_deployer.import.failed", error=str(e),
                  message="Deployment functionality disabled for local development")

logger = structlog.get_logger()

router = APIRouter()


# ============================================================================
# Pydantic Schemas
# ============================================================================

class DeployInstanceRequest(BaseModel):
    """Request to deploy new MemMachine instance"""
    name: str = Field(..., min_length=1, max_length=255, description="Instance name")
    openai_api_key: str = Field(..., min_length=20, description="OpenAI API key")
    description: str | None = Field(None, max_length=1000)

    class Config:
        json_schema_extra = {
            "example": {
                "name": "My MemMachine",
                "openai_api_key": "sk-...",
                "description": "Production memory instance"
            }
        }


class InstanceResponse(BaseModel):
    """Instance details response"""
    id: str
    name: str
    slug: str
    url: str
    status: str
    health_status: str
    created_at: str
    deployed_at: str | None

    class Config:
        from_attributes = True


class DeploymentResponse(BaseModel):
    """Deployment result"""
    instance_id: str
    url: str
    status: str
    message: str


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/deploy", response_model=DeploymentResponse, status_code=status.HTTP_201_CREATED)
async def deploy_memmachine_instance(
    request: DeployInstanceRequest,
    # TODO: Add authentication dependency
    # current_user: User = Depends(get_current_user)
):
    """
    Deploy a new MemMachine instance to GCP.

    This endpoint:
    1. Creates a Cloud SQL instance (PostgreSQL + pgvector)
    2. Deploys Neo4j to Cloud Run
    3. Deploys MemMachine to Cloud Run
    4. Returns the MemMachine URL

    **Deployment time:** 60-90 seconds

    **Cost:** ~$0 when idle (scale-to-zero), ~$0.10/hour when active
    """
    # TODO: Get real user_id from authentication
    user_id = "demo-user"  # Placeholder

    logger.info(
        "api.instances.deploy.started",
        user_id=user_id,
        name=request.name
    )

    try:
        # Check if deployer is available
        if not DEPLOYER_AVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Deployment functionality not available in development mode. Deploy to GCP to enable."
            )

        # Deploy the stack
        deployer = MemMachineDeployer()
        instance = await deployer.deploy_complete_stack(
            user_id=user_id,
            instance_name=request.name,
            openai_api_key=request.openai_api_key,
        )

        # TODO: Save to database when DB connection is working
        # For now, skip database persistence - just deploy and return

        logger.info(
            "api.instances.deploy.completed",
            instance_id=instance.id,
            url=instance.cloud_run_url
        )

        return DeploymentResponse(
            instance_id=instance.id,
            url=instance.cloud_run_url,
            status="deployed",
            message=f"MemMachine deployed successfully! Access at: {instance.cloud_run_url}"
        )

    except DeploymentError as e:
        logger.error(
            "api.instances.deploy.failed",
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Deployment failed: {str(e)}"
        )

    except Exception as e:
        logger.error(
            "api.instances.deploy.error",
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during deployment"
        )


@router.get("", response_model=List[InstanceResponse])
async def list_instances(
    user_id: str = Query(..., description="User ID to filter instances"),
    instance_status: Optional[str] = Query(None, description="Filter by status (creating, running, stopped, failed)"),
    db: AsyncSession = Depends(get_db_session),
    # current_user: User = Depends(get_current_user)
):
    """
    List all MemMachine instances for a user.

    Can optionally filter by status.
    """
    # Build query
    query = select(Instance).where(Instance.user_id == user_id)

    # Apply status filter if provided
    if instance_status:
        try:
            status_enum = InstanceStatus(instance_status)
            query = query.where(Instance.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status: {instance_status}. Must be one of: creating, running, stopped, failed, deleted"
            )

    # Exclude soft-deleted instances unless explicitly requested
    if instance_status != "deleted":
        query = query.where(Instance.deleted_at.is_(None))

    # Order by creation date (newest first)
    query = query.order_by(Instance.created_at.desc())

    # Execute query
    result = await db.execute(query)
    instances = result.scalars().all()

    logger.info(
        "api.instances.list",
        user_id=user_id,
        count=len(instances),
        status_filter=instance_status
    )

    return [
        InstanceResponse(
            id=inst.id,
            name=inst.name,
            slug=inst.slug,
            url=inst.cloud_run_url or "",
            status=inst.status.value,
            health_status=inst.health_status,
            created_at=inst.created_at.isoformat(),
            deployed_at=inst.deployed_at.isoformat() if inst.deployed_at else None
        )
        for inst in instances
    ]


@router.get("/{instance_id}", response_model=InstanceResponse)
async def get_instance(
    instance_id: str,
    user_id: str = Query(..., description="User ID for authorization"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get details of a specific MemMachine instance.

    Verifies that the requesting user owns the instance.
    """
    result = await db.execute(
        select(Instance).where(
            and_(
                Instance.id == instance_id,
                Instance.user_id == user_id
            )
        )
    )
    instance = result.scalar_one_or_none()

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance {instance_id} not found or not owned by user"
        )

    logger.info("api.instances.get", instance_id=instance_id, user_id=user_id)

    return InstanceResponse(
        id=instance.id,
        name=instance.name,
        slug=instance.slug,
        url=instance.cloud_run_url or "",
        status=instance.status.value,
        health_status=instance.health_status,
        created_at=instance.created_at.isoformat(),
        deployed_at=instance.deployed_at.isoformat() if instance.deployed_at else None
    )


@router.delete("/{instance_id}", status_code=status.HTTP_200_OK)
async def delete_instance(
    instance_id: str,
    user_id: str = Query(..., description="User ID for authorization"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Delete a MemMachine instance and all associated resources.

    This will:
    - Stop and delete the Cloud Run services (MemMachine + Neo4j)
    - Delete the Cloud SQL instance
    - Remove secrets from Secret Manager

    WARNING: This is a destructive operation and cannot be undone!
    """
    result = await db.execute(
        select(Instance).where(
            and_(
                Instance.id == instance_id,
                Instance.user_id == user_id
            )
        )
    )
    instance = result.scalar_one_or_none()

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance {instance_id} not found or not owned by user"
        )

    # Check if already deleted
    if instance.status == InstanceStatus.DELETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Instance is already deleted"
        )

    logger.info("api.instances.delete.started", instance_id=instance_id, user_id=user_id)

    # Mark as deleting
    instance.status = InstanceStatus.DELETING
    await db.commit()

    # Track deletion results
    deleted_resources = []
    deletion_errors = []

    try:
        # Delete GCP resources using deployer (best effort - don't fail if resources don't exist)
        if DEPLOYER_AVAILABLE:
            deployer = MemMachineDeployer()

            # Delete MemMachine service
            if instance.cloud_run_service_name:
                try:
                    await deployer._delete_cloud_run_service(instance.cloud_run_service_name)
                    logger.info("Deleted MemMachine service", service=instance.cloud_run_service_name)
                    deleted_resources.append(f"Cloud Run service: {instance.cloud_run_service_name}")
                except Exception as e:
                    logger.warning("Failed to delete MemMachine service", error=str(e))
                    deletion_errors.append(f"MemMachine service: {str(e)}")

            # Delete Neo4j service
            if instance.neo4j_service_name:
                try:
                    await deployer._delete_cloud_run_service(instance.neo4j_service_name)
                    logger.info("Deleted Neo4j service", service=instance.neo4j_service_name)
                    deleted_resources.append(f"Neo4j service: {instance.neo4j_service_name}")
                except Exception as e:
                    logger.warning("Failed to delete Neo4j service", error=str(e))
                    deletion_errors.append(f"Neo4j service: {str(e)}")

            # Delete Cloud SQL instance
            if instance.postgres_instance_name:
                try:
                    await deployer._delete_cloud_sql(instance.postgres_instance_name)
                    logger.info("Deleted PostgreSQL instance", instance=instance.postgres_instance_name)
                    deleted_resources.append(f"PostgreSQL instance: {instance.postgres_instance_name}")
                except Exception as e:
                    logger.warning("Failed to delete PostgreSQL instance", error=str(e))
                    deletion_errors.append(f"PostgreSQL instance: {str(e)}")

            # Delete secrets
            for secret_name in [instance.openai_secret_name, instance.postgres_secret_name, instance.neo4j_secret_name]:
                if secret_name:
                    try:
                        await deployer._delete_secret(secret_name)
                        deleted_resources.append(f"Secret: {secret_name}")
                    except Exception as e:
                        logger.warning(f"Failed to delete secret {secret_name}", error=str(e))
                        deletion_errors.append(f"Secret {secret_name}: {str(e)}")

        # Mark as deleted in database (soft delete) - ALWAYS do this even if resource deletion fails
        instance.status = InstanceStatus.DELETED
        instance.deleted_at = datetime.utcnow()
        await db.commit()

        logger.info("api.instances.delete.completed",
                   instance_id=instance_id,
                   deleted_count=len(deleted_resources),
                   error_count=len(deletion_errors))

        message = f"Instance marked as deleted in database."
        if deleted_resources:
            message += f" Successfully deleted {len(deleted_resources)} resource(s)."
        if deletion_errors:
            message += f" {len(deletion_errors)} resource(s) could not be deleted (may not exist)."

        return {
            "status": "deleted",
            "instance_id": instance_id,
            "message": message,
            "deleted_resources": deleted_resources,
            "deletion_errors": deletion_errors
        }

    except Exception as e:
        logger.error(
            "api.instances.delete.failed",
            instance_id=instance_id,
            error=str(e),
            exc_info=True
        )

        # Try to update status back to failed
        try:
            instance.status = InstanceStatus.FAILED
            instance.deployment_error = f"Deletion failed: {str(e)}"
            await db.commit()
        except:
            pass

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete instance: {str(e)}"
        )


@router.post("/{instance_id}/start", response_model=dict)
async def start_instance(
    instance_id: str,
    user_id: str = Query(..., description="User ID for authorization"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Start a stopped MemMachine instance by setting min_instances to 1.
    """
    result = await db.execute(
        select(Instance).where(
            and_(
                Instance.id == instance_id,
                Instance.user_id == user_id
            )
        )
    )
    instance = result.scalar_one_or_none()

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance {instance_id} not found or not owned by user"
        )

    if instance.status != InstanceStatus.STOPPED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Instance must be in STOPPED state to start (current: {instance.status})"
        )

    logger.info("api.instances.start.started", instance_id=instance_id, user_id=user_id)

    try:
        if DEPLOYER_AVAILABLE:
            deployer = MemMachineDeployer()
            await deployer._update_cloud_run_min_instances(
                instance.cloud_run_service_name,
                min_instances=1
            )

        # Update database
        instance.status = InstanceStatus.RUNNING
        instance.min_instances = 1
        await db.commit()

        logger.info("api.instances.start.completed", instance_id=instance_id)

        return {
            "status": "running",
            "instance_id": instance_id,
            "message": "Instance has been started"
        }

    except Exception as e:
        logger.error("api.instances.start.failed", instance_id=instance_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start instance: {str(e)}"
        )


@router.post("/{instance_id}/stop", response_model=dict)
async def stop_instance(
    instance_id: str,
    user_id: str = Query(..., description="User ID for authorization"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Stop a running MemMachine instance by setting min_instances to 0 (scale to zero).

    This pauses the instance to save costs while keeping data intact.
    """
    result = await db.execute(
        select(Instance).where(
            and_(
                Instance.id == instance_id,
                Instance.user_id == user_id
            )
        )
    )
    instance = result.scalar_one_or_none()

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance {instance_id} not found or not owned by user"
        )

    if instance.status != InstanceStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Instance must be in RUNNING state to stop (current: {instance.status})"
        )

    logger.info("api.instances.stop.started", instance_id=instance_id, user_id=user_id)

    try:
        if DEPLOYER_AVAILABLE:
            deployer = MemMachineDeployer()
            await deployer._update_cloud_run_min_instances(
                instance.cloud_run_service_name,
                min_instances=0
            )

        # Update database
        instance.status = InstanceStatus.STOPPED
        instance.min_instances = 0
        await db.commit()

        logger.info("api.instances.stop.completed", instance_id=instance_id)

        return {
            "status": "stopped",
            "instance_id": instance_id,
            "message": "Instance has been stopped (scaled to zero)"
        }

    except Exception as e:
        logger.error("api.instances.stop.failed", instance_id=instance_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop instance: {str(e)}"
        )
