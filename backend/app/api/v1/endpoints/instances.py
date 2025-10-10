"""
Instance Management API Endpoints
Handles MemMachine instance deployments
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

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
    db: AsyncSession = Depends(get_db_session),
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
    user_id = "user-123"  # Placeholder

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

        # Save to database
        db.add(instance)
        await db.commit()
        await db.refresh(instance)

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
    db: AsyncSession = Depends(get_db_session),
    # current_user: User = Depends(get_current_user)
):
    """
    List all MemMachine instances for the current user.
    """
    # TODO: Get real user_id
    user_id = "user-123"

    # Query instances
    from sqlalchemy import select
    result = await db.execute(
        select(Instance).where(Instance.user_id == user_id)
    )
    instances = result.scalars().all()

    return [
        InstanceResponse(
            id=inst.id,
            name=inst.name,
            slug=inst.slug,
            url=inst.cloud_run_url,
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
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get details of a specific MemMachine instance.
    """
    from sqlalchemy import select

    result = await db.execute(
        select(Instance).where(Instance.id == instance_id)
    )
    instance = result.scalar_one_or_none()

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instance not found"
        )

    return InstanceResponse(
        id=instance.id,
        name=instance.name,
        slug=instance.slug,
        url=instance.cloud_run_url,
        status=instance.status.value,
        health_status=instance.health_status,
        created_at=instance.created_at.isoformat(),
        deployed_at=instance.deployed_at.isoformat() if instance.deployed_at else None
    )


@router.delete("/{instance_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_instance(
    instance_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Delete a MemMachine instance and all associated resources.

    This will:
    - Stop and delete the Cloud Run services (MemMachine + Neo4j)
    - Delete the Cloud SQL instance
    - Remove secrets from Secret Manager
    """
    from sqlalchemy import select

    result = await db.execute(
        select(Instance).where(Instance.id == instance_id)
    )
    instance = result.scalar_one_or_none()

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instance not found"
        )

    logger.info("api.instances.delete.started", instance_id=instance_id)

    try:
        # TODO: Delete GCP resources
        # - Cloud Run services
        # - Cloud SQL instance
        # - Secrets

        # Update status
        instance.status = InstanceStatus.DELETED
        instance.deleted_at = datetime.utcnow()

        await db.commit()

        logger.info("api.instances.delete.completed", instance_id=instance_id)

    except Exception as e:
        logger.error(
            "api.instances.delete.failed",
            instance_id=instance_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete instance: {str(e)}"
        )


@router.post("/{instance_id}/start", response_model=InstanceResponse)
async def start_instance(
    instance_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Start a stopped MemMachine instance.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Start/stop functionality coming soon"
    )


@router.post("/{instance_id}/stop", response_model=InstanceResponse)
async def stop_instance(
    instance_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Stop a running MemMachine instance (scale to zero).
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Start/stop functionality coming soon"
    )
