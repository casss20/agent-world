    request_id = Column(String(120), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    
    # HTTP context
    route = Column(String(255), nullable=True)
    method = Column(String(10), nullable=True)
    status_code = Column(Integer, nullable=True)
    
    # Details
    details = Column(JSONB, default={})
    
    # Integrity
    prev_hash = Column(String(128), nullable=True)
    event_hash = Column(String(128), nullable=False)
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_audit_actor', 'actor_type', 'actor_id', 'created_at'),
        Index('ix_audit_action', 'action', 'created_at'),
        Index('ix_audit_resource', 'resource_type', 'resource_id'),
        Index('ix_audit_request', 'request_id'),
        Index('ix_audit_created', 'created_at'),
    )


class Asset(Base):
    """
    File assets for businesses (images, videos, documents)
    
    Stores metadata about uploaded files with references to
    external storage (S3/Cloudinary)
    """
    __tablename__ = "assets"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Ownership
    business_id = Column(String(36), ForeignKey("businesses.id"), nullable=False)
    business = relationship("Business", back_populates="assets")
    
    # File metadata
    filename = Column(String(255), nullable=False)
    storage_path = Column(String(500), nullable=False)  # S3 key or Cloudinary public_id
    public_url = Column(String(1000), nullable=False)
    thumbnail_url = Column(String(1000), nullable=True)
    
    # Asset properties
    type = Column(String(50), nullable=False, default="content")  # content, thumbnail, logo, document
    mime_type = Column(String(100), nullable=True)
    size_bytes = Column(Integer, nullable=True)
    
    # Review workflow
    status = Column(String(20), default="pending_review")  # pending_review, approved, rejected, archived
    
    # Organization
    tags = Column(ARRAY(String), default=[])
    description = Column(Text, nullable=True)
    
    # Upload tracking
    uploaded_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    uploader = relationship("User", foreign_keys=[uploaded_by])
    
    # Approval tracking
    approved_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    approver = relationship("User", foreign_keys=[approved_by])
    approved_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_asset_business', 'business_id', 'created_at'),
        Index('ix_asset_status', 'status', 'business_id'),
        Index('ix_asset_type', 'type', 'business_id'),
    )


# Update Business model to include assets relationship
# Add to Business class: assets = relationship("Asset", back_populates="business", cascade="all, delete-orphan")

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_current_blackboard_state(db_session, room_id: uuid.UUID) -> Dict:
    """Build current blackboard state from event sourcing"""
    events = db_session.query(BlackboardEvent).filter(
        BlackboardEvent.room_id == room_id
    ).order_by(BlackboardEvent.sequence_number.asc()).all()
    
    state = {}
    for event in events:
        if event.operation == BlackboardOperation.SET:
            state[event.key] = event.value
        elif event.operation == BlackboardOperation.DELETE:
            state.pop(event.key, None)
        elif event.operation == BlackboardOperation.APPEND:
            if event.key not in state:
                state[event.key] = []
            if isinstance(state[event.key], list):
                state[event.key].append(event.value)
    
    return state

def get_room_member_count(db_session, room_id: uuid.UUID) -> int:
    """Get current active member count for a room"""
    return db_session.query(AgentRoom).filter(
        AgentRoom.room_id == room_id,
        AgentRoom.is_active == True
    ).count()
