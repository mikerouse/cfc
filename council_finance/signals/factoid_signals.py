"""
Real-time Factoid Signals

This module sets up Django signals to automatically maintain factoid dependencies
and invalidate instances when data changes, ensuring real-time responsiveness.
"""
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.utils import timezone
import logging

from ..models import (
    FactoidTemplate, 
    FactoidInstance, 
    FactoidFieldDependency,
    DataField,
    CouncilCharacteristic,
    FinancialFigure,
)
from ..services.factoid_engine import FactoidEngine

logger = logging.getLogger(__name__)


@receiver(post_save, sender=FactoidTemplate)
def update_factoid_template_dependencies(sender, instance, created, **kwargs):
    """
    Update field dependencies when a factoid template is saved
    """
    try:
        engine = FactoidEngine()
        engine.update_field_dependencies(instance)
        
        if created:
            logger.info(f"Created new factoid template: {instance.name}")
        else:
            logger.info(f"Updated factoid template: {instance.name}")
            
    except Exception as e:
        logger.error(f"Error updating template dependencies for {instance.name}: {e}")


@receiver(post_save, sender=DataField)
def handle_data_field_change(sender, instance, created, **kwargs):
    """
    Handle changes to data fields - invalidate dependent factoids
    """
    try:
        if not created:  # Only for updates, not new fields
            engine = FactoidEngine()
            engine.invalidate_instances_for_field(instance)
            logger.info(f"Invalidated factoids dependent on field: {instance.name}")
            
    except Exception as e:
        logger.error(f"Error handling field change for {instance.name}: {e}")


@receiver(post_delete, sender=DataField)
def handle_data_field_deletion(sender, instance, **kwargs):
    """
    Handle data field deletion - clean up dependencies
    """
    try:
        # Remove dependencies
        FactoidFieldDependency.objects.filter(field=instance).delete()
        
        # Mark related templates for validation
        templates_to_validate = FactoidTemplate.objects.filter(
            referenced_fields__contains=[instance.variable_name]
        )
        
        for template in templates_to_validate:
            template.validation_errors = template.validation_errors or []
            template.validation_errors.append(f"Field '{instance.variable_name}' was deleted")
            template.save()
        
        logger.info(f"Cleaned up dependencies for deleted field: {instance.name}")
        
    except Exception as e:
        logger.error(f"Error handling field deletion for {instance.name}: {e}")


@receiver(post_save, sender=CouncilCharacteristic)
def handle_council_characteristic_change(sender, instance, created, **kwargs):
    """
    Invalidate factoids when council characteristics change
    """
    try:
        # Find factoids that might be affected
        field_name = instance.field.variable_name if instance.field else None
        
        if field_name:
            # Invalidate instances for this council and field
            affected_instances = FactoidInstance.objects.filter(
                council=instance.council,
                financial_year=instance.year,
                template__referenced_fields__contains=[field_name]
            )
            
            affected_instances.update(expires_at=timezone.now())
            
            count = affected_instances.count()
            if count > 0:
                logger.info(f"Invalidated {count} factoid instances due to characteristic change: {field_name}")
                
    except Exception as e:
        logger.error(f"Error handling characteristic change: {e}")


@receiver(post_save, sender=FinancialFigure)
def handle_financial_figure_change(sender, instance, created, **kwargs):
    """
    Invalidate factoids when financial figures change
    """
    try:
        # Find factoids that might be affected
        field_name = instance.field.variable_name if instance.field else None
        
        if field_name:
            # Invalidate instances for this council and field
            affected_instances = FactoidInstance.objects.filter(
                council=instance.council,
                financial_year=instance.year,
                template__referenced_fields__contains=[field_name]
            )
            
            affected_instances.update(expires_at=timezone.now())
            
            count = affected_instances.count()
            if count > 0:
                logger.info(f"Invalidated {count} factoid instances due to financial figure change: {field_name}")
                
    except Exception as e:
        logger.error(f"Error handling financial figure change: {e}")


@receiver(pre_save, sender=FactoidTemplate)
def validate_factoid_template_before_save(sender, instance, **kwargs):
    """
    Validate template before saving and extract field references
    """
    try:
        # Extract referenced fields
        instance.extract_referenced_fields()
        
        # Validate template
        instance.validate_template()
        instance.last_validated = timezone.now()
        
        logger.debug(f"Validated template {instance.name} - found {len(instance.referenced_fields)} field references")
        
    except Exception as e:
        logger.error(f"Error validating template {instance.name}: {e}")
        # Add validation error but don't prevent saving
        instance.validation_errors = instance.validation_errors or []
        instance.validation_errors.append(f"Validation error: {str(e)}")


# Real-time WebSocket signals (if using channels)
try:
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    
    channel_layer = get_channel_layer()
    
    @receiver(post_save, sender=FactoidInstance)
    def broadcast_factoid_update(sender, instance, created, **kwargs):
        """
        Broadcast factoid updates via WebSocket for real-time UI updates
        """
        try:
            if channel_layer:
                group_name = f"factoids_{instance.council.slug}_{instance.financial_year.year}"
                
                message = {
                    'type': 'factoid_update',
                    'data': {
                        'instance_id': instance.id,
                        'template_name': instance.template.name,
                        'rendered_text': instance.rendered_text,
                        'council_slug': instance.council.slug,
                        'year': instance.financial_year.year,
                        'counter_slug': instance.counter.slug if instance.counter else None,
                        'created': created,
                    }
                }
                
                async_to_sync(channel_layer.group_send)(group_name, message)
                logger.debug(f"Broadcasted factoid update for {instance}")
                
        except ImportError:
            # Channels not available
            pass
        except Exception as e:
            logger.error(f"Error broadcasting factoid update: {e}")

except ImportError:
    # Channels not installed
    logger.debug("Channels not available - WebSocket broadcasting disabled")
    pass
