import os

from django.shortcuts import render
from django.conf import settings

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .serializers import *
from .models import *

from openai import OpenAI

# Setup Vector DB and RAG stuff
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

# Actual prompting
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage


@api_view(['POST'])
def report_create(request):
    if request.method == 'POST':
        serializer = ReportSerializer(data=request.data) # Serialiser for incoming JSON data
        if serializer.is_valid():
            serializer.save() # Pushes to database
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# LangChain API 4:42
@api_view(['POST'])
def query_chatgpt(request):

    # Set up model
    model = ChatOpenAI(model="gpt-4o", temperature=0.5)

    # Set up prompt and user question
    user_question = request.data.get("message", "")
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", "You are a psychologist and executive coach analyzing psychometric assessment reports for a client."),
        ("user", "{user_question}"),
    ])

    # Set up chain
    chain = prompt_template | model
    result = chain.invoke({"user_question": user_question})

    return Response({"response": result.content})


# Run when change PDF set to setup/update vector store based on data in RAG_data folder
@api_view(['POST'])
def setup_vector_db(request):
    data_folder = os.path.join(settings.BASE_DIR, "RAG_data")# Maybe add kosh_feedback if this don't work
    all_chunks = []

    # Chunk all PDFs
    for filename in os.listdir(data_folder):
        if filename.endswith(".pdf"):
            pdf_path = os.path.join(data_folder, filename)
            loader = PyPDFLoader(pdf_path)
            docs = loader.load()

            text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
            chunks = text_splitter.split_documents(docs)
            all_chunks.extend(chunks)

    # Embed all chunks
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    db = FAISS.from_documents(all_chunks, embeddings)

    # Save vectorstore
    index_dir = os.path.join(settings.BASE_DIR, "vectorstores", "sample_index")
    os.makedirs(index_dir, exist_ok=True)
    db.save_local(index_dir)

    return Response({"message": f"Indexed {len(all_chunks)} chunks from {len(os.listdir(data_folder))} PDF(s)."})