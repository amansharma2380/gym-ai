from rest_framework import serializers
from .models import ProgressEntry

class ProgressEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProgressEntry
        fields = ['id','date','weight_kg','body_fat_pct','notes']
