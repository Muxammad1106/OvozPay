from rest_framework import serializers
from apps.users.models import User, Referral, UserSettings


class ReferralSerializer(serializers.ModelSerializer):
    referrer_phone = serializers.CharField(source='referrer.phone_number', read_only=True)
    
    class Meta:
        model = Referral
        fields = ['id', 'referrer', 'referrer_phone', 'referral_code', 'created_at']
        read_only_fields = ['id', 'created_at', 'referrer_phone']


class UserSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSettings
        fields = ['id', 'currency', 'notify_reports', 'notify_goals', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserSerializer(serializers.ModelSerializer):
    settings = UserSettingsSerializer(read_only=True)
    referral_info = ReferralSerializer(source='referral', read_only=True)
    source_name = serializers.CharField(source='source.name', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'phone_number', 'language', 'referral', 'referral_info', 
            'source', 'source_name', 'is_active', 'settings', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'referral_info', 'source_name', 'settings']
    
    def validate_phone_number(self, value):
        if not value.startswith('+'):
            raise serializers.ValidationError("Номер телефона должен начинаться с +")
        if len(value) < 10:
            raise serializers.ValidationError("Номер телефона слишком короткий")
        return value 