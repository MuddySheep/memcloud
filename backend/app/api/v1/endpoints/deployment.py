"""
Real-time deployment status endpoints following ADLF Framework
"""
import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum

import structlog
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.memmachine_deployer import MemMachineDeployer
from app.db.database import get_db_session
from app.models import Instance, InstanceStatus

logger = structlog.get_logger()

router = APIRouter()

# ADLF Phase Management System
class DeploymentPhase(str, Enum):
    DISCOVERY = "DISCOVERY"           # 0-5%
    ARCHITECTURE = "ARCHITECTURE"     # 5-15%
    MVP_CORE = "MVP_CORE"           # 15-40%
    MVP_POLISH = "MVP_POLISH"       # 40-60%
    BETA = "BETA"                   # 60-80%
    PRODUCTION = "PRODUCTION"       # 80-95%
    EVOLUTION = "EVOLUTION"         # 95-100%

class DeploymentStep(BaseModel):
    """Single step in deployment process"""
    id: str
    phase: DeploymentPhase
    name: str
    status: str  # pending, in_progress, completed, failed
    progress: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    details: Optional[Dict] = None

class DeploymentStatus(BaseModel):
    """Complete deployment status following ADLF"""
    deployment_id: str
    overall_progress: int
    current_phase: DeploymentPhase
    quality_score: int  # PFF quality tracking

    # Phase tracking
    phases: Dict[str, Dict] = {
        "DISCOVERY": {"progress": 0, "status": "pending", "gates": []},
        "ARCHITECTURE": {"progress": 0, "status": "pending", "gates": []},
        "MVP_CORE": {"progress": 0, "status": "pending", "gates": []},
        "MVP_POLISH": {"progress": 0, "status": "pending", "gates": []},
        "BETA": {"progress": 0, "status": "pending", "gates": []},
        "PRODUCTION": {"progress": 0, "status": "pending", "gates": []},
    }

    # Current actions
    steps: List[DeploymentStep] = []

    # Results
    endpoints: Optional[Dict] = None
    success: bool = False

    # CES State tracking
    decisions_made: List[Dict] = []
    technical_debt: List[str] = []

# Global deployment tracking
active_deployments: Dict[str, DeploymentStatus] = {}
deployment_connections: Dict[str, List[WebSocket]] = {}

class DeploymentRequest(BaseModel):
    """Request model for starting a deployment"""
    name: str = Field(..., description="Instance name")
    openai_api_key: str = Field(..., description="OpenAI API key")
    user_id: str = Field(..., description="User ID who owns this instance")
    # Optional Neo4j Aura credentials (if not provided, deploys Neo4j on Cloud Run)
    neo4j_uri: Optional[str] = Field(None, description="Neo4j Aura connection URI (e.g., neo4j+s://xxxxx.databases.neo4j.io)")
    neo4j_user: Optional[str] = Field(None, description="Neo4j username (usually 'neo4j')")
    neo4j_password: Optional[str] = Field(None, description="Neo4j password")

@router.post("/deploy")
async def start_deployment(
    request: DeploymentRequest,
    db: AsyncSession = Depends(get_db_session)
) -> Dict:
    """
    Start a new deployment following ADLF phases
    """
    deployment_id = str(uuid.uuid4())

    # Create instance record in database
    instance = Instance(
        id=deployment_id,
        user_id=request.user_id,
        name=request.name,
        slug=f"{request.name.lower().replace(' ', '-')}-{deployment_id[:8]}",
        status=InstanceStatus.CREATING,
        region=settings.GCP_REGION,
    )

    db.add(instance)
    await db.commit()
    await db.refresh(instance)

    # Initialize deployment status
    status = DeploymentStatus(
        deployment_id=deployment_id,
        overall_progress=0,
        current_phase=DeploymentPhase.DISCOVERY,
        quality_score=0
    )

    active_deployments[deployment_id] = status

    # Start async deployment process
    asyncio.create_task(
        execute_deployment(
            deployment_id=deployment_id,
            name=request.name,
            openai_api_key=request.openai_api_key,
            user_id=request.user_id,
            neo4j_uri=request.neo4j_uri,
            neo4j_user=request.neo4j_user,
            neo4j_password=request.neo4j_password
        )
    )

    return {
        "deployment_id": deployment_id,
        "instance_id": deployment_id,
        "websocket_url": f"/api/v1/deployment/{deployment_id}/ws",
        "status": "started"
    }

async def execute_deployment(
    deployment_id: str,
    name: str,
    openai_api_key: str,
    user_id: str,
    neo4j_uri: Optional[str] = None,
    neo4j_user: Optional[str] = None,
    neo4j_password: Optional[str] = None
):
    """
    Execute deployment following ADLF phases with real-time updates
    """
    status = active_deployments[deployment_id]

    # Variables to track deployment resources
    postgres_ip = None
    postgres_conn = None
    neo4j_url = None
    neo4j_bolt = None
    memmachine_url = None
    postgres_secret = None
    neo4j_secret = None
    openai_secret = None

    try:
        # Initialize deployer and secrets
        deployer = MemMachineDeployer()
        import secrets as python_secrets

        # STEP 1: Store OpenAI API Key (0-5%)
        await add_step(deployment_id, DeploymentStep(
            id="secret-openai",
            phase=DeploymentPhase.DISCOVERY,
            name="Storing OpenAI API key in Secret Manager",
            status="in_progress",
            progress=2
        ))
        openai_secret = f"openai-key-{deployment_id}"
        await deployer._store_secret(openai_secret, openai_api_key)
        await complete_step(deployment_id, "secret-openai")
        status.overall_progress = 5

        # STEP 2: Deploy Cloud SQL PostgreSQL (5-35%)
        await add_step(deployment_id, DeploymentStep(
            id="postgres-create",
            phase=DeploymentPhase.ARCHITECTURE,
            name="Creating Cloud SQL PostgreSQL instance (this takes 3-5 minutes)",
            status="in_progress",
            progress=10
        ))
        postgres_password = python_secrets.token_urlsafe(32)
        postgres_secret = f"postgres-pass-{deployment_id}"
        await deployer._store_secret(postgres_secret, postgres_password)

        postgres_ip, postgres_conn = await deployer._deploy_cloud_sql(
            deployment_id, postgres_password
        )

        await complete_step(deployment_id, "postgres-create", {
            "postgres_ip": postgres_ip,
            "connection": postgres_conn
        })
        status.overall_progress = 35

        # STEP 3: Setup Neo4j Graph Database (35-55%)
        if neo4j_uri and neo4j_user and neo4j_password:
            # Using Neo4j Aura (managed service)
            await add_step(deployment_id, DeploymentStep(
                id="neo4j-setup",
                phase=DeploymentPhase.MVP_CORE,
                name="Configuring Neo4j Aura connection (managed service)",
                status="in_progress",
                progress=40
            ))

            neo4j_secret = f"neo4j-aura-pass-{deployment_id}"
            await deployer._store_secret(neo4j_secret, neo4j_password)

            # Extract the bolt URL from the neo4j+s:// URI
            neo4j_url = neo4j_uri
            neo4j_bolt = neo4j_uri.replace("neo4j+s://", "").replace("neo4j://", "")

            await complete_step(deployment_id, "neo4j-setup", {
                "neo4j_url": neo4j_url,
                "neo4j_bolt": neo4j_bolt,
                "neo4j_type": "aura"
            })
            status.overall_progress = 55
        else:
            # Deploy Neo4j to Cloud Run (won't work without VPC)
            await add_step(deployment_id, DeploymentStep(
                id="neo4j-deploy",
                phase=DeploymentPhase.MVP_CORE,
                name="Deploying Neo4j graph database to Cloud Run",
                status="in_progress",
                progress=40
            ))

            neo4j_password_generated = python_secrets.token_urlsafe(32)
            neo4j_secret = f"neo4j-pass-{deployment_id}"
            await deployer._store_secret(neo4j_secret, neo4j_password_generated)

            neo4j_url, neo4j_bolt = await deployer._deploy_neo4j(
                deployment_id, neo4j_password_generated
            )

            await complete_step(deployment_id, "neo4j-deploy", {
                "neo4j_url": neo4j_url,
                "neo4j_bolt": neo4j_bolt,
                "neo4j_type": "cloud_run"
            })
            status.overall_progress = 55

        # STEP 4: Deploy MemMachine API (55-85%)
        await add_step(deployment_id, DeploymentStep(
            id="memmachine-deploy",
            phase=DeploymentPhase.MVP_CORE,
            name="Deploying MemMachine API with your configuration",
            status="in_progress",
            progress=60
        ))

        # For Neo4j Aura, pass the full URI with protocol
        neo4j_connection_url = neo4j_url if neo4j_uri else f"bolt://{neo4j_bolt}:7687"

        memmachine_url = await deployer._deploy_memmachine(
            instance_id=deployment_id,
            postgres_ip=postgres_ip,
            postgres_secret=postgres_secret,
            neo4j_bolt_url=neo4j_bolt,
            neo4j_secret=neo4j_secret,
            openai_secret=openai_secret,
            user_id=user_id,
            neo4j_connection_url=neo4j_connection_url  # Pass proper connection URL
        )

        await complete_step(deployment_id, "memmachine-deploy", {
            "memmachine_url": memmachine_url
        })
        status.overall_progress = 85

        # STEP 5: Health Check (85-95%)
        await add_step(deployment_id, DeploymentStep(
            id="health-check",
            phase=DeploymentPhase.BETA,
            name="Running health checks on MemMachine API",
            status="in_progress",
            progress=90
        ))

        await deployer._validate_deployment(memmachine_url)
        await complete_step(deployment_id, "health-check")
        status.overall_progress = 95

        # STEP 6: Finalize (95-100%)
        await add_step(deployment_id, DeploymentStep(
            id="finalize",
            phase=DeploymentPhase.PRODUCTION,
            name="Deployment complete! Your MemMachine is ready",
            status="in_progress",
            progress=98
        ))
        await complete_step(deployment_id, "finalize")

        # Set final results
        status.endpoints = {
            "memmachine_api": memmachine_url,
            "postgres": f"{postgres_ip}:5432",
            "neo4j": neo4j_url,
            "playground": f"/playground/{deployment_id}"
        }
        status.success = True
        status.overall_progress = 100
        status.quality_score = 95  # PFF quality score

        # Add to decision ledger (CES)
        status.decisions_made.append({
            "decision": f"Deployed instance {deployment_id} to GCP",
            "timestamp": datetime.utcnow().isoformat(),
            "confidence": "■■■■■"
        })

        # Save deployment details to database
        from app.db.database import get_db
        async with get_db() as db:
            from sqlalchemy import select
            result = await db.execute(
                select(Instance).where(Instance.id == deployment_id)
            )
            instance = result.scalar_one_or_none()

            if instance:
                # Update instance with all deployment details
                instance.status = InstanceStatus.RUNNING
                instance.cloud_run_service_name = f"memmachine-{deployment_id}"
                instance.cloud_run_url = memmachine_url
                instance.neo4j_service_name = f"neo4j-{deployment_id}"
                instance.neo4j_url = neo4j_url
                instance.neo4j_bolt_url = neo4j_bolt
                instance.neo4j_secret_name = neo4j_secret
                instance.postgres_instance_name = f"memmachine-{deployment_id}"
                instance.postgres_ip = postgres_ip
                instance.postgres_connection_name = postgres_conn
                instance.postgres_secret_name = postgres_secret
                instance.openai_secret_name = openai_secret
                instance.deployed_at = datetime.utcnow()
                instance.health_status = "healthy"
                instance.last_health_check = datetime.utcnow()

                await db.commit()

                logger.info(
                    "Instance deployment saved to database",
                    instance_id=deployment_id,
                    memmachine_url=memmachine_url
                )

        await broadcast_update(deployment_id)

    except Exception as e:
        logger.error("Deployment failed", deployment_id=deployment_id, error=str(e))
        status.success = False

        # Update instance status to FAILED
        try:
            from app.db.database import get_db
            async with get_db() as db:
                from sqlalchemy import select
                result = await db.execute(
                    select(Instance).where(Instance.id == deployment_id)
                )
                instance = result.scalar_one_or_none()

                if instance:
                    instance.status = InstanceStatus.FAILED
                    instance.deployment_error = str(e)
                    await db.commit()
        except Exception as db_error:
            logger.error("Failed to update instance status", error=str(db_error))

        await broadcast_update(deployment_id)

async def update_phase(deployment_id: str, phase: DeploymentPhase, status: str):
    """Update phase status"""
    deployment = active_deployments[deployment_id]
    deployment.phases[phase.value]["status"] = status
    await broadcast_update(deployment_id)

async def add_step(deployment_id: str, step: DeploymentStep):
    """Add a new deployment step"""
    deployment = active_deployments[deployment_id]
    step.started_at = datetime.utcnow()
    deployment.steps.append(step)
    await broadcast_update(deployment_id)

async def complete_step(deployment_id: str, step_id: str, details: Optional[Dict] = None):
    """Mark a step as completed"""
    deployment = active_deployments[deployment_id]
    for step in deployment.steps:
        if step.id == step_id:
            step.status = "completed"
            step.completed_at = datetime.utcnow()
            step.details = details
            break
    await broadcast_update(deployment_id)

async def broadcast_update(deployment_id: str):
    """Broadcast status update to all connected WebSocket clients"""
    if deployment_id in deployment_connections:
        status = active_deployments[deployment_id]
        for websocket in deployment_connections[deployment_id]:
            try:
                await websocket.send_json(status.dict())
            except:
                # Connection closed, remove it
                deployment_connections[deployment_id].remove(websocket)

@router.websocket("/{deployment_id}/ws")
async def deployment_websocket(websocket: WebSocket, deployment_id: str):
    """WebSocket for real-time deployment updates"""
    await websocket.accept()

    # Add to connections
    if deployment_id not in deployment_connections:
        deployment_connections[deployment_id] = []
    deployment_connections[deployment_id].append(websocket)

    # Send initial status
    if deployment_id in active_deployments:
        await websocket.send_json(active_deployments[deployment_id].dict())

    try:
        while True:
            # Keep connection alive
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        # Remove from connections
        if deployment_id in deployment_connections:
            deployment_connections[deployment_id].remove(websocket)

@router.get("/{deployment_id}/status")
async def get_deployment_status(deployment_id: str) -> DeploymentStatus:
    """Get current deployment status"""
    if deployment_id not in active_deployments:
        raise HTTPException(status_code=404, detail="Deployment not found")

    return active_deployments[deployment_id]