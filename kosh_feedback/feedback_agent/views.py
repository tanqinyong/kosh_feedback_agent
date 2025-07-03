from django.shortcuts import render
from django.conf import settings

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .serializers import *
from .models import *

from openai import OpenAI


@api_view(['POST'])
def report_create(request):
    if request.method == 'POST':
        serializer = ReportSerializer(data=request.data) # Serialiser for incoming JSON data
        if serializer.is_valid():
            serializer.save() # Pushes to database
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def query_chatgpt(request):
    user_question = request.data.get("message", "")
    system_prompt = "You are a psychologist and executive coach analyzing psychometric assessment reports for a client."

    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_question}
    ]

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.5,
            max_tokens=500
        )
        content = response.choices[0].message.content
        return Response({"response": content})
    
    except Exception as e:
        return Response({"error": str(e)}, status=500)
