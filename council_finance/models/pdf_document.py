"""
PDF Document Model

Manages secure storage and serving of PDF files uploaded for financial data extraction.
Tracks processing status, user associations, and file metadata for the PDF.js integration.
"""

import os
import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings
from django.core.files.storage import default_storage
from .council import Council, FinancialYear


def pdf_upload_path(instance, filename):
    """
    Generate secure upload path for PDF files.
    Format: pdfs/YYYY/MM/DD/council_slug/uuid_filename.pdf
    """
    # Ensure filename is safe
    name, ext = os.path.splitext(filename)
    safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).rstrip()
    safe_filename = f"{uuid.uuid4().hex[:8]}_{safe_name}{ext}"
    
    # Create date-based directory structure
    upload_date = timezone.now()
    return f"pdfs/{upload_date.year:04d}/{upload_date.month:02d}/{upload_date.day:02d}/{instance.council.slug if instance.council else 'unknown'}/{safe_filename}"


class PDFDocument(models.Model):
    """
    PDF Document model for secure file storage and access control.
    
    Features:
    - Secure file storage with UUID-based paths
    - User and council associations for access control
    - Processing status tracking
    - Metadata extraction and storage
    - File integrity verification
    """
    
    # Processing status choices
    PROCESSING_PENDING = 'pending'
    PROCESSING_IN_PROGRESS = 'processing'
    PROCESSING_COMPLETED = 'completed'
    PROCESSING_FAILED = 'failed'
    PROCESSING_CANCELLED = 'cancelled'
    
    PROCESSING_STATUS_CHOICES = [
        (PROCESSING_PENDING, 'Pending Processing'),
        (PROCESSING_IN_PROGRESS, 'Processing in Progress'),
        (PROCESSING_COMPLETED, 'Processing Completed'),
        (PROCESSING_FAILED, 'Processing Failed'),
        (PROCESSING_CANCELLED, 'Processing Cancelled'),
    ]
    
    # Core identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    original_filename = models.CharField(max_length=255, help_text="Original filename when uploaded")
    
    # File storage
    file = models.FileField(
        upload_to=pdf_upload_path,
        help_text="The PDF file itself",
        max_length=500
    )
    file_size = models.PositiveIntegerField(null=True, blank=True, help_text="File size in bytes")
    file_hash = models.CharField(
        max_length=64, 
        null=True, 
        blank=True, 
        help_text="SHA-256 hash for integrity verification"
    )
    
    # Associations
    council = models.ForeignKey(
        Council,
        on_delete=models.CASCADE,
        related_name='pdf_documents',
        help_text="Council this PDF relates to"
    )
    financial_year = models.ForeignKey(
        FinancialYear,
        on_delete=models.CASCADE,
        related_name='pdf_documents',
        help_text="Financial year this PDF covers"
    )
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_pdfs',
        help_text="User who uploaded this PDF"
    )
    
    # Processing status
    processing_status = models.CharField(
        max_length=20,
        choices=PROCESSING_STATUS_CHOICES,
        default=PROCESSING_PENDING,
        help_text="Current processing status"
    )
    processing_started_at = models.DateTimeField(null=True, blank=True)
    processing_completed_at = models.DateTimeField(null=True, blank=True)
    processing_error = models.TextField(
        null=True,
        blank=True,
        help_text="Error message if processing failed"
    )
    
    # PDF metadata (extracted during processing)
    page_count = models.PositiveSmallIntegerField(null=True, blank=True)
    pdf_title = models.CharField(max_length=500, null=True, blank=True)
    pdf_author = models.CharField(max_length=200, null=True, blank=True)
    pdf_subject = models.CharField(max_length=500, null=True, blank=True)
    pdf_creator = models.CharField(max_length=200, null=True, blank=True)
    pdf_producer = models.CharField(max_length=200, null=True, blank=True)
    pdf_creation_date = models.DateTimeField(null=True, blank=True)
    pdf_modification_date = models.DateTimeField(null=True, blank=True)
    
    # Access control
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this PDF is active and accessible"
    )
    access_token = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        help_text="Secure access token for PDF viewing"
    )
    access_expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the access token expires"
    )
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_accessed_at = models.DateTimeField(null=True, blank=True)
    access_count = models.PositiveIntegerField(default=0)
    
    # Analysis results (JSON field for extracted data)
    extraction_results = models.JSONField(
        null=True,
        blank=True,
        help_text="Results from AI/regex extraction process"
    )
    confidence_scores = models.JSONField(
        null=True,
        blank=True,
        help_text="Confidence scores for each extracted field"
    )
    
    class Meta:
        db_table = 'council_finance_pdfdocument'
        indexes = [
            models.Index(fields=['council', 'financial_year']),
            models.Index(fields=['uploaded_by', 'created_at']),
            models.Index(fields=['processing_status', 'created_at']),
            models.Index(fields=['access_token']),
            models.Index(fields=['is_active', 'created_at']),
        ]
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.original_filename} ({self.council.name}, {self.financial_year.label})"
    
    def save(self, *args, **kwargs):
        """Override save to generate access token and calculate file hash"""
        # Generate access token if not present
        if not self.access_token:
            self.generate_access_token()
            
        # Set file size if not present and file exists
        if self.file and not self.file_size:
            try:
                self.file_size = self.file.size
            except (ValueError, OSError):
                pass
                
        super().save(*args, **kwargs)
    
    def generate_access_token(self, hours_valid=24):
        """Generate a new secure access token"""
        import secrets
        self.access_token = secrets.token_urlsafe(48)
        self.access_expires_at = timezone.now() + timezone.timedelta(hours=hours_valid)
    
    def is_access_token_valid(self):
        """Check if the current access token is still valid"""
        if not self.access_token or not self.access_expires_at:
            return False
        return timezone.now() < self.access_expires_at
    
    def refresh_access_token(self, hours_valid=24):
        """Generate new access token and save"""
        self.generate_access_token(hours_valid)
        self.save(update_fields=['access_token', 'access_expires_at'])
    
    def record_access(self):
        """Record that this PDF was accessed"""
        self.last_accessed_at = timezone.now()
        self.access_count += 1
        self.save(update_fields=['last_accessed_at', 'access_count'])
    
    def can_be_accessed_by(self, user):
        """Check if a user can access this PDF"""
        if not self.is_active:
            return False
            
        if not user or not user.is_authenticated:
            return False
            
        # Admin users can access all PDFs
        if user.is_staff or user.is_superuser:
            return True
            
        # Owner can access
        if self.uploaded_by == user:
            return True
            
        # Add other access rules here (e.g., council staff, experts)
        # For now, restrict to uploader and admin
        return False
    
    def get_secure_url(self, request=None):
        """Get secure URL for accessing this PDF"""
        from django.urls import reverse
        if not self.is_access_token_valid():
            self.refresh_access_token()
            
        return reverse('pdf_serve', kwargs={
            'document_id': str(self.id),
            'access_token': self.access_token
        })
    
    def start_processing(self):
        """Mark processing as started"""
        self.processing_status = self.PROCESSING_IN_PROGRESS
        self.processing_started_at = timezone.now()
        self.save(update_fields=['processing_status', 'processing_started_at'])
    
    def complete_processing(self, extraction_results=None, confidence_scores=None):
        """Mark processing as completed with optional results"""
        self.processing_status = self.PROCESSING_COMPLETED
        self.processing_completed_at = timezone.now()
        if extraction_results:
            self.extraction_results = extraction_results
        if confidence_scores:
            self.confidence_scores = confidence_scores
        self.save(update_fields=[
            'processing_status', 'processing_completed_at',
            'extraction_results', 'confidence_scores'
        ])
    
    def fail_processing(self, error_message):
        """Mark processing as failed with error message"""
        self.processing_status = self.PROCESSING_FAILED
        self.processing_error = str(error_message)[:2000]  # Limit error message length
        self.save(update_fields=['processing_status', 'processing_error'])
    
    def get_file_url(self):
        """Get the file URL (for internal use)"""
        if self.file:
            return self.file.url
        return None
    
    def delete_file(self):
        """Delete the physical file from storage"""
        if self.file:
            try:
                default_storage.delete(self.file.name)
            except Exception as e:
                # Log error but don't raise - model deletion should succeed
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to delete PDF file {self.file.name}: {e}")
    
    def delete(self, *args, **kwargs):
        """Override delete to remove physical file"""
        self.delete_file()
        super().delete(*args, **kwargs)


class PDFProcessingLog(models.Model):
    """
    Log entries for PDF processing operations.
    Tracks individual steps and their outcomes for debugging and monitoring.
    """
    
    LOG_LEVELS = [
        ('debug', 'Debug'),
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('critical', 'Critical'),
    ]
    
    pdf_document = models.ForeignKey(
        PDFDocument,
        on_delete=models.CASCADE,
        related_name='processing_logs'
    )
    level = models.CharField(max_length=10, choices=LOG_LEVELS, default='info')
    step = models.CharField(
        max_length=100,
        help_text="Processing step (e.g., 'text_extraction', 'ai_analysis')"
    )
    message = models.TextField(help_text="Log message")
    data = models.JSONField(
        null=True,
        blank=True,
        help_text="Additional structured data for this log entry"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'council_finance_pdfprocessinglog'
        indexes = [
            models.Index(fields=['pdf_document', 'created_at']),
            models.Index(fields=['level', 'created_at']),
        ]
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.pdf_document.original_filename} - {self.level}: {self.step}"