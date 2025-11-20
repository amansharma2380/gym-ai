from rest_framework import serializers
from .models import ProgressEntry
from .models import Progress


class ProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Progress
        fields = ['id', 'date', 'weight_kg', 'body_fat_pct', 'notes']
        # if you also want member info, you can do:
        # fields = ['id', 'member', 'date', 'weight_kg', 'body_fat_pct', 'notes']


# class ProgressEntrySerializer(serializers.ModelSerializer):
#     class Meta:
#         model = ProgressEntry
#         fields = ['id','date','weight_kg','body_fat_pct','notes']
