from django.shortcuts import render

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .serializers import *

from .models import *

@api_view(['POST'])
def report_create(request):
    if request.method == 'POST':
        serializer = ReportSerializer(data=request.data) # Serialiser for incoming JSON data
        if serializer.is_valid():
            serializer.save() # Pushes to database
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

