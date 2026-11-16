"""
File Upload Routes - S3/Cloudinary Integration
Backend wiring for AssetLibrary file management
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
import boto3
import uuid
import os
from datetime import datetime

# Optional cloudinary import
try:
    import cloudinary
    import cloudinary.uploader
    from cloudinary.utils import cloudinary_url
    CLOUDINARY_AVAILABLE = True
except ImportError:
    CLOUDINARY_AVAILABLE = False
    cloudinary = None  # type: ignore
    cloudinary_url = None  # type: ignore

# Import models
from database import get_db
from sqlalchemy.orm import Session
from models import Asset, Business, AuditLog

from infrastructure.interfaces.base_storage_provider import BaseStorageProvider

# Import auth
from auth import get_current_user

router = APIRouter(prefix="/files", tags=["files"])

# Configuration from environment
S3_BUCKET = os.getenv("S3_BUCKET_NAME", "agent-world-assets")
S3_REGION = os.getenv("AWS_REGION", "us-east-1")
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")

# Initialize Cloudinary if configured
if CLOUDINARY_AVAILABLE and CLOUDINARY_CLOUD_NAME:
    cloudinary.config(
        cloud_name=CLOUDINARY_CLOUD_NAME,
        api_key=CLOUDINARY_API_KEY,
        api_secret=CLOUDINARY_API_SECRET,
    )

# ── S3 Client ─────────────────────────────────────────────────────────────────
s3_client = boto3.client("s3", region_name=S3_REGION)


# ── Pydantic Models ───────────────────────────────────────────────────────────
class FileUploadResponse(BaseModel):
    file_id: str
    url: str
    public_url: Optional[str]
    mime_type: str
    size_bytes: int
    uploaded_by: str
    uploaded_at: datetime
    provider: str  # "s3" or "cloudinary"
    status: str


class FileListResponse(BaseModel):
    files: List[dict]
    total: int
    business_id: str


class FileUpdateRequest(BaseModel):
    name: Optional[str]
    tags: Optional[List[str]]
    metadata: Optional[dict]


class FileDeleteResponse(BaseModel):
    file_id: str
    status: str
    deleted_at: datetime


# ── Upload Endpoints ──────────────────────────────────────────────────────────

@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    business_id: str = Form(...),
    tags: Optional[str] = Form(None),  # comma-separated
    upload_provider: str = Form("s3"),  # "s3" or "cloudinary"
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Upload a file to S3 or Cloudinary"""
    
    file_id = str(uuid.uuid4())
    file_content = await file.read()
    file_size = len(file_content)
    mime_type = file.content_type or "application/octet-stream"
    
    # Generate filename
    original_name = file.filename or "unnamed"
    file_extension = os.path.splitext(original_name)[1]
    storage_key = f"{business_id}/{file_id}{file_extension}"
    
    url = None
    public_url = None
    provider_used = upload_provider
    
    try:
        if upload_provider == "cloudinary" and CLOUDINARY_AVAILABLE:
            # Upload to Cloudinary
            upload_result = cloudinary.uploader.upload(
                file_content,
                public_id=file_id,
                folder=business_id,
                resource_type="auto",
            )
            url = upload_result["secure_url"]
            public_url = upload_result.get("url")
            provider_used = "cloudinary"
            
        else:
            # Upload to S3
            s3_client.put_object(
                Bucket=S3_BUCKET,
                Key=storage_key,
                Body=file_content,
                ContentType=mime_type,
                Metadata={
                    "uploaded_by": current_user.get("id", "unknown"),
                    "original_name": original_name,
                    "business_id": business_id,
                },
            )
            url = f"https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/{storage_key}"
            public_url = url
            provider_used = "s3"
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
    
    # Save to database
    asset = Asset(
        id=file_id,
        business_id=business_id,
        name=original_name,
        url=url,
        public_url=public_url,
        mime_type=mime_type,
        size_bytes=file_size,
        provider=provider_used,
        storage_key=storage_key if provider_used == "s3" else None,
        uploaded_by=current_user.get("id", "unknown"),
        tags=tags.split(",") if tags else [],
        status="active",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(asset)
    
    # Audit log
    audit = AuditLog(
        id=str(uuid.uuid4()),
        action="file_uploaded",
        actor_id=current_user.get("id", "unknown"),
        target_id=file_id,
        details={
            "business_id": business_id,
            "provider": provider_used,
            "size_bytes": file_size,
            "mime_type": mime_type,
        },
        created_at=datetime.utcnow(),
    )
    db.add(audit)
    db.commit()
    
    return FileUploadResponse(
        file_id=file_id,
        url=url,
        public_url=public_url,
        mime_type=mime_type,
        size_bytes=file_size,
        uploaded_by=current_user.get("id", "unknown"),
        uploaded_at=datetime.utcnow(),
        provider=provider_used,
        status="active",
    )


@router.post("/upload-multiple", response_model=List[FileUploadResponse])
async def upload_multiple_files(
    files: List[UploadFile] = File(...),
    business_id: str = Form(...),
    tags: Optional[str] = Form(None),
    upload_provider: str = Form("s3"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Upload multiple files at once"""
    responses = []
    for file in files:
        result = await upload_file(
            file=file,
            business_id=business_id,
            tags=tags,
            upload_provider=upload_provider,
            db=db,
            current_user=current_user,
        )
        responses.append(result)
    return responses


# ── List & Get Endpoints ────────────────────────────────────────────────────

@router.get("/business/{business_id}", response_model=FileListResponse)
async def list_business_files(
    business_id: str,
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List all files for a business"""
    
    query = db.query(Asset).filter(Asset.business_id == business_id)
    
    if status:
        query = query.filter(Asset.status == status)
    
    total = query.count()
    files = query.order_by(Asset.created_at.desc()).offset(offset).limit(limit).all()
    
    return FileListResponse(
        files=[
            {
                "file_id": f.id,
                "name": f.name,
                "url": f.url,
                "mime_type": f.mime_type,
                "size_bytes": f.size_bytes,
                "provider": f.provider,
                "status": f.status,
                "uploaded_at": f.created_at,
                "tags": f.tags,
            }
            for f in files
        ],
        total=total,
        business_id=business_id,
    )


@router.get("/{file_id}", response_model=FileUploadResponse)
async def get_file(
    file_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get a specific file"""
    
    asset = db.query(Asset).filter(Asset.id == file_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileUploadResponse(
        file_id=asset.id,
        url=asset.url,
        public_url=asset.public_url,
        mime_type=asset.mime_type,
        size_bytes=asset.size_bytes,
        uploaded_by=asset.uploaded_by,
        uploaded_at=asset.created_at,
        provider=asset.provider,
        status=asset.status,
    )


# ── Update & Delete Endpoints ────────────────────────────────────────────────

@router.patch("/{file_id}", response_model=FileUploadResponse)
async def update_file(
    file_id: str,
    update: FileUpdateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Update file metadata"""
    
    asset = db.query(Asset).filter(Asset.id == file_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="File not found")
    
    if update.name:
        asset.name = update.name
    if update.tags is not None:
        asset.tags = update.tags
    if update.metadata:
        asset.metadata = update.metadata
    
    asset.updated_at = datetime.utcnow()
    
    # Audit log
    audit = AuditLog(
        id=str(uuid.uuid4()),
        action="file_updated",
        actor_id=current_user.get("id", "unknown"),
        target_id=file_id,
        details={"fields_updated": list(update.dict(exclude_none=True).keys())},
        created_at=datetime.utcnow(),
    )
    db.add(audit)
    db.commit()
    
    return FileUploadResponse(
        file_id=asset.id,
        url=asset.url,
        public_url=asset.public_url,
        mime_type=asset.mime_type,
        size_bytes=asset.size_bytes,
        uploaded_by=asset.uploaded_by,
        uploaded_at=asset.created_at,
        provider=asset.provider,
        status=asset.status,
    )


@router.delete("/{file_id}", response_model=FileDeleteResponse)
async def delete_file(
    file_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Delete a file (soft delete from DB + remove from storage)"""
    
    asset = db.query(Asset).filter(Asset.id == file_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Delete from storage
    try:
        if asset.provider == "s3" and asset.storage_key:
            s3_client.delete_object(Bucket=S3_BUCKET, Key=asset.storage_key)
        elif asset.provider == "cloudinary" and CLOUDINARY_AVAILABLE:
            cloudinary.uploader.destroy(asset.id)
    except Exception as e:
        # Log but continue - file might already be gone
        print(f"Storage delete warning: {e}")
    
    # Soft delete in DB
    asset.status = "deleted"
    asset.updated_at = datetime.utcnow()
    
    # Audit log
    audit = AuditLog(
        id=str(uuid.uuid4()),
        action="file_deleted",
        actor_id=current_user.get("id", "unknown"),
        target_id=file_id,
        details={"provider": asset.provider, "storage_key": asset.storage_key},
        created_at=datetime.utcnow(),
    )
    db.add(audit)
    db.commit()
    
    return FileDeleteResponse(
        file_id=file_id,
        status="deleted",
        deleted_at=datetime.utcnow(),
    )


# ── Signed URL Endpoints ────────────────────────────────────────────────────

@router.get("/{file_id}/signed-url")
async def get_signed_url(
    file_id: str,
    expires_in: int = 3600,  # seconds
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get a presigned URL for temporary access"""
    
    asset = db.query(Asset).filter(Asset.id == file_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="File not found")
    
    if asset.provider == "s3":
        try:
            signed_url = s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": S3_BUCKET, "Key": asset.storage_key},
                ExpiresIn=expires_in,
            )
            return {"signed_url": signed_url, "expires_in": expires_in}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to generate signed URL: {str(e)}")
    
    elif asset.provider == "cloudinary" and CLOUDINARY_AVAILABLE:
        try:
            url, options = cloudinary_url(
                asset.id,
                secure=True,
                sign_url=True,
                expiration=expires_in,
            )
            return {"signed_url": url, "expires_in": expires_in}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to generate signed URL: {str(e)}")
    
    else:
        return {"url": asset.url, "note": "Provider does not support signed URLs"}
