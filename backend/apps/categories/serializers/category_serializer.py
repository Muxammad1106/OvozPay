from rest_framework import serializers
from apps.categories.models import Category


class CategorySerializer(serializers.ModelSerializer):
    user_phone = serializers.CharField(source='user.phone_number', read_only=True)
    
    class Meta:
        model = Category
        fields = [
            'id', 'user', 'user_phone', 'name', 'type', 'is_default',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'user_phone']
    
    def validate_name(self, value):
        if len(value.strip()) < 2:
            raise serializers.ValidationError("Название категории должно содержать минимум 2 символа")
        return value.strip()
    
    def validate(self, data):
        user = data.get('user')
        name = data.get('name')
        category_type = data.get('type')
        
        if user and name and category_type:
            existing = Category.objects.filter(
                user=user, 
                name=name, 
                type=category_type
            ).exclude(pk=self.instance.pk if self.instance else None)
            
            if existing.exists():
                raise serializers.ValidationError(
                    "Категория с таким названием и типом уже существует"
                )
        
        return data 