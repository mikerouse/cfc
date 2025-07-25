"""
Factoid API Serializers

Serializers for the factoid system API endpoints.
"""
from rest_framework import serializers
from ..models.factoid import (
    FactoidTemplate,
    FactoidInstance,
    FactoidFieldDependency,
)
from ..models.field import DataField


class DataFieldSerializer(serializers.ModelSerializer):
    """
    Serializer for DataField model
    """
    formatting_options = serializers.SerializerMethodField()
    sample_value = serializers.SerializerMethodField()
    
    class Meta:
        model = DataField
        fields = [
            'id', 'name', 'variable_name', 'description', 
            'category', 'data_type', 'is_active',
            'formatting_options', 'sample_value'
        ]
        read_only_fields = ['id']
    
    def get_formatting_options(self, obj):
        """Get available formatting options for this field type"""
        if obj.data_type in ['decimal', 'integer']:
            return ['default', 'currency', 'number', 'percentage']
        elif obj.data_type == 'percentage':
            return ['percentage', 'decimal']
        else:
            return ['default']
    
    def get_sample_value(self, obj):
        """Get sample value for preview"""
        sample_values = {
            'text': 'Sample Text',
            'integer': 123456,
            'decimal': 123456.78,
            'percentage': 15.5,
            'boolean': True,
            'date': '2024-01-01',
        }
        return sample_values.get(obj.data_type, 'Sample Value')


class FactoidFieldDependencySerializer(serializers.ModelSerializer):
    """
    Serializer for field dependencies
    """
    field_name = serializers.CharField(source='field.name', read_only=True)
    field_variable = serializers.CharField(source='field.variable_name', read_only=True)
    
    class Meta:
        model = FactoidFieldDependency
        fields = ['id', 'field', 'field_name', 'field_variable', 'is_critical']


class FactoidTemplateSerializer(serializers.ModelSerializer):
    """
    Serializer for FactoidTemplate model
    """
    referenced_fields = serializers.JSONField(read_only=True)
    validation_errors = serializers.JSONField(read_only=True)
    dependencies = FactoidFieldDependencySerializer(
        source='factoidfielddependency_set', 
        many=True, 
        read_only=True
    )
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    
    # Display choices
    factoid_type_display = serializers.CharField(source='get_factoid_type_display', read_only=True)
    color_scheme_display = serializers.CharField(source='get_color_scheme_display', read_only=True)
    
    class Meta:
        model = FactoidTemplate
        fields = [
            'id', 'name', 'slug', 'template_text', 'factoid_type', 'factoid_type_display',
            'emoji', 'color_scheme', 'color_scheme_display', 'priority', 'is_active',
            'min_value', 'max_value', 'requires_previous_year', 'animation_duration',
            'flip_animation', 'referenced_fields', 'validation_errors', 'dependencies',
            'created_at', 'updated_at', 'created_by', 'created_by_name'
        ]
        read_only_fields = [
            'id', 'slug', 'referenced_fields', 'validation_errors', 
            'created_at', 'updated_at', 'created_by'
        ]
    
    def validate_template_text(self, value):
        """
        Validate template text syntax
        """
        if not value.strip():
            raise serializers.ValidationError("Template text cannot be empty")
        
        # Check for balanced braces
        open_braces = value.count('{')
        close_braces = value.count('}')
        if open_braces != close_braces:
            raise serializers.ValidationError("Template has mismatched braces")
        
        return value
    
    def validate_priority(self, value):
        """
        Validate priority is within reasonable range
        """
        if value < 0 or value > 100:
            raise serializers.ValidationError("Priority must be between 0 and 100")
        return value
    
    def validate_animation_duration(self, value):
        """
        Validate animation duration
        """
        if value < 1000 or value > 30000:
            raise serializers.ValidationError("Animation duration must be between 1000ms and 30000ms")
        return value


class FactoidInstanceSerializer(serializers.ModelSerializer):
    """
    Serializer for FactoidInstance model
    """
    template_name = serializers.CharField(source='template.name', read_only=True)
    template_emoji = serializers.CharField(source='template.emoji', read_only=True)
    template_color = serializers.CharField(source='template.color_scheme', read_only=True)
    council_name = serializers.CharField(source='council.name', read_only=True)
    council_slug = serializers.CharField(source='council.slug', read_only=True)
    year_label = serializers.CharField(source='financial_year.year', read_only=True)
    counter_name = serializers.CharField(source='counter.name', read_only=True)
    counter_slug = serializers.CharField(source='counter.slug', read_only=True)
    is_expired_flag = serializers.SerializerMethodField()
    
    class Meta:
        model = FactoidInstance
        fields = [
            'id', 'template', 'template_name', 'template_emoji', 'template_color',
            'council', 'council_name', 'council_slug', 'financial_year', 'year_label',
            'counter', 'counter_name', 'counter_slug', 'rendered_text', 'computed_data',
            'relevance_score', 'is_significant', 'computed_at', 'expires_at', 'is_expired_flag'
        ]
        read_only_fields = [
            'id', 'rendered_text', 'computed_data', 'relevance_score', 
            'computed_at', 'expires_at'
        ]
    
    def get_is_expired_flag(self, obj):
        """Check if this instance is expired"""
        return obj.is_expired()


class FactoidPreviewSerializer(serializers.Serializer):
    """
    Serializer for factoid preview requests
    """
    template_text = serializers.CharField(required=True)
    council_slug = serializers.CharField(required=False)
    year_slug = serializers.CharField(required=False, default='2023-24')
    counter_slug = serializers.CharField(required=False)
    
    def validate_template_text(self, value):
        """Validate template text"""
        if not value.strip():
            raise serializers.ValidationError("Template text is required")
        return value


class FieldDiscoverySerializer(serializers.Serializer):
    """
    Serializer for field discovery responses
    """
    category = serializers.CharField(required=False)
    search_query = serializers.CharField(required=False)
    limit = serializers.IntegerField(min_value=1, max_value=100, default=50)


class QuickValidationSerializer(serializers.Serializer):
    """
    Serializer for quick template validation
    """
    template_text = serializers.CharField(required=True)
    
    def validate_template_text(self, value):
        """Basic validation"""
        if not value.strip():
            raise serializers.ValidationError("Template text is required")
        return value
