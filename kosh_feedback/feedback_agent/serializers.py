from rest_framework import serializers

from .models import Report

# Edit this according to pdf format
class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = '__all__'