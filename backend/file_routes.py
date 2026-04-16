"""
File Upload Routes - S3/Cloudinary Integration
Backend wiring for AssetLibrary file management
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
import boto3
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url
import uuid
import os
from datetime import datetime

# Import models
from database import get_db
from sqlalchemy.orm import Session
from models import Asset, Business, AuditLog

# Import auth
from auth import get_current_user

router = APIRouter(prefix="/files", tags=["files"])

# Configuration from environment
S3_BUCKET = os.getenv("S3_BUCKET_NAME", "agent-world-assets")
S3_REGION = os.getenv("AWS_REGION", "us-east-1")
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")
UPLOAD_PROVIDER = os.getenv("UPLOAD_PROVIDER", "s3")  # 's3' or 'cloudinary'

# Initialize Cloudinary if configured
if CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET:
    cloudinary.config(
        cloud_name=CLOUDINARY_CLOUD_NAME,
        api_key=CLOUDINARY_API_KEY,
        api_secret=CLOUDINARY_API_SECRET,
        secure=True
    )

# Initialize S3 client
s3_client = boto3.client(
    's3',
    region_name=S3_REGION,
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
)


class AssetUploadResponse(BaseModel):
    id: str
    filename: str
    url: str
    thumbnail_url: Optional[str]
    type: str
    size: int
    status: str
    created_at: str


class AssetListResponse(BaseModel):
    assets: List[dict]
    total: int


@router.post("/upload", response_model=AssetUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    business_id: str = Form(...),
    asset_type: str = Form("content"),  # content, thumbnail, logo, etc.
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload a file to S3 or Cloudinary and create asset record
    """
    # Verify business ownership
    business = db.query(Business).filter(
        Business.id == business_id,
        Business.owner_id == current_user["id"]
    ).first()
    
    if not business:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Generate unique filename
    file_ext = file.filename.split('.')[-1].lower()
    unique_id = str(uuid.uuid4())
    safe_filename = f"{unique_id}.{file_ext}"
    
    # Read file content
    content = await file.read()
    file_size = len(content)
    
    # Upload based on provider
    if UPLOAD_PROVIDER == "cloudinary" and CLOUDINARY_CLOUD_NAME:
        result = await upload_to_cloudinary(content, safe_filename, file.content_type)
    else:
        result = await upload_to_s3(content, safe_filename, file.content_type)
    
    # Create asset record
    asset = Asset(
        id=unique_id,
        business_id=business_id,
        filename=file.filename,
        storage_path=result["path"],
        public_url=result["url"],
        thumbnail_url=result.get("thumbnail_url"),
        type=asset_type,
        mime_type=file.content_type,
        size_bytes=file_size,
        status="pending_review",
        uploaded_by=current_user["id"],
        description=description,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(asset)
    
    # Create audit log
    audit_log = AuditLog(
        id=str(uuid.uuid4()),
        business_id=business_id,
        action="asset_uploaded",
        actor_id=current_user["id"],
        details={
            "asset_id": unique_id,
            "filename": file.filename,
            "size": file_size,
            "type": asset_type
        },
        created_at=datetime.utcnow()
    )
    db.add(audit_log)
    db.commit()
    
    return AssetUploadResponse(
        id=unique_id,
        filename=file.filename,
        url=result["url"],
        thumbnail_url=result.get("thumbnail_url"),
        type=asset_type,
        size=file_size,
        status="pending_review",
        created_at=asset.created_at.isoformat()
    )


async def upload_to_cloudinary(content: bytes, filename: str, content_type: str):
    """Upload to Cloudinary with automatic optimization"""
    import io
    
    # Determine resource type
    resource_type = "image" if content_type.startswith("image/") else "raw"
    
    # Upload
    result = cloudinary.uploader.upload(
        io.BytesIO(content),
        public_id=filename.split('.')[0],
        resource_type=resource_type,
        folder="agent-world/assets",
        overwrite=False
    )
    
    # Generate optimized URL
    if resource_type == "image":
        thumbnail_url, _ = cloudinary_url(
            result["public_id"],
            width=300,
            height=300,
            crop="fit",
            quality="auto"
        )
    else:
        thumbnail_url = None
    
    return {
        "path": result["public_id"],
        "url": result["secure_url"],
        "thumbnail_url": thumbnail_url
    }


async def upload_to_s3(content: bytes, filename: str, content_type: str):
    """Upload to S3 with presigned URL generation"""
    s3_key = f"assets/{filename}"
    
    # Upload
    s3_client.put_object(
        Bucket=S3_BUCKET,
        Key=s3_key,
        Body=content,
        ContentType=content_type,
        Metadata={
            "original-filename": filename
        }
    )
    
    # Generate presigned URL (valid for 1 week)
    url = s3_client.generate_presigned_url(
        'get_object',
        Params={'Bucket': S3_BUCKET, 'Key': s3_key},
        ExpiresIn=604800
    )
    
    # Generate thumbnail URL for images
    thumbnail_url = None
    if content_type.startswith("image/"):
        # For images, we could use S3 + Lambda@Edge or just return the same URL
        # In production, you'd want a thumbnail service
        thumbnail_url = url  # Simplified - same URL for now
    
    return {
        "path": s3_key,
        "url": url,
        "thumbnail_url": thumbnail_url
    }


@router.get("/business/{business_id}", response_model=AssetListResponse)
async def list_business_assets(
    business_id: str,
    asset_type: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    List assets for a business with filtering
    """
    # Verify business ownership
    business = db.query(Business).filter(
        Business.id == business_id,
        Business.owner_id == current_user["id"]
    ).first()
    
    if not business:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Build query
    query = db.query(Asset).filter(Asset.business_id == business_id)
    
    if asset_type:
        query = query.filter(Asset.type == asset_type)
    
    if status:
        query = query.filter(Asset.status == status)
    
    if search:
        query = query.filter(Asset.filename.ilike(f"%{search}%"))
    
    total = query.count()
    assets = query.order_by(Asset.created_at.desc()).offset(offset).limit(limit).all()
    
    return AssetListResponse(
        assets=[{
            "id": a.id,
            "filename": a.filename,
            "url": a.public_url,
            "thumbnail_url": a.thumbnail_url,
            "type": a.type,
            "status": a.status,
            "size": a.size_bytes,
            "created_at": a.created_at.isoformat(),
            "tags": a.tags or []
        } for a in assets],
        total=total
    )


@router.post("/{asset_id}/approve")
async def approve_asset(
    asset_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Approve an asset for use (triggers agent notification)
    """
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # Verify business ownership
    business = db.query(Business).filter(
        Business.id == asset.business_id,
        Business.owner_id == current_user["id"]
    ).first()
    
    if not business:
        raise HTTPException(status_code=403, detail="Access denied")
    
    asset.status = "approved"
    asset.updated_at = datetime.utcnow()
    
    # Create audit log
    audit_log = AuditLog(
        id=str(uuid.uuid4()),
        business_id=asset.business_id,
        action="asset_approved",
        actor_id=current_user["id"],
        details={"asset_id": asset_id, "filename": asset.filename},
        created_at=datetime.utcnow()
    )
    db.add(audit_log)
    db.commit()
    
    return {"status": "approved", "asset_id": asset_id}


@router.delete("/{asset_id}")
async def delete_asset(
    asset_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete an asset from storage and database
    """
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # Verify business ownership
    business = db.query(Business).filter(
        Business.id == asset.business_id,
        Business.owner_id == current_user["id"]
    ).first()
    
    if not business:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Delete from storage
    try:
        if UPLOAD_PROVIDER == "cloudinary":
            cloudinary.uploader.destroy(asset.storage_path)
        else:
            s3_client.delete_object(Bucket=S3_BUCKET, Key=asset.storage_path)
    except Exception as e:
        # Log error but continue to delete DB record
        print(f"Error deleting from storage: {e}")
    
    # Create audit log before deletion
    audit_log = AuditLog(
        id=str(uuid.uuid4()),
        business_id=asset.business_id,
        action="asset_deleted",
        actor_id=current_user["id"],
        details={"asset_id": asset_id, "filename": asset.filename},
        created_at=datetime.utcnow()
    )
    db.add(audit_log)
    
    # Delete from database
    db.delete(asset)
    db.commit()
    
    return {"status": "deleted", "asset_id": asset_id}


@router.patch("/{asset_id}")
async def update_asset(
    asset_id: str,
    tags: Optional[List[str]] = None,
    description: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Update asset metadata (tags, description)
    """
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # Verify business ownership
    business = db.query(Business).filter(
        Business.id == asset.business_id,
        Business.owner_id == current_user["id"]
    ).first()
    
    if not business:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if tags is not None:
        asset.tags = tags
    
    if description is not None:
        asset.description = description
    
    asset.updated_at = datetime.utcnow()
    db.commit()
    
    return {
        "id": asset.id,
        "tags": asset.tags,
        "description": asset.description,
        "updated_at": asset.updated_at.isoformat()
    }
