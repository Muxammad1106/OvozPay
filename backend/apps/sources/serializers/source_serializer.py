from rest_framework import serializers
from apps.sources.models import Source


class SourceSerializer(serializers.ModelSerializer):
    users_count = serializers.SerializerMethodField()
    active_users_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Source
        fields = [
            'id', 'name', 'description', 'utm_source', 'utm_medium',
            'utm_campaign', 'is_active', 'users_count', 'active_users_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'users_count', 'active_users_count'
        ]
    
    def get_users_count(self, obj):
        return obj.get_users_count()
    
    def get_active_users_count(self, obj):
        return obj.get_active_users_count()
    
    def validate_name(self, value):
        if len(value.strip()) < 2:
            raise serializers.ValidationError("Название источника должно содержать минимум 2 символа")
        return value.strip().lower() 