import os
import tempfile

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
from langchain_community.document_loaders import PyMuPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS

# Actual prompting
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain

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
    user_question = request.POST.get("message")  # Full chat history string
    files = request.FILES.getlist("files")  # List of uploaded PDF files

    user_doc_text = process_pdf_files(files)
    message = f"User uploaded report:\n{user_doc_text}\n\nQuestion:\n{user_question}"

    try:
        vectorstore = load_vector_db()
        chain = build_rag_chain(vectorstore)
        result = chain.invoke({"input": message})
        return Response({"response": result["answer"]})
    except Exception as e:
        return Response({"error": str(e)}, status=500)

# Process all user PDFs as texts
def process_pdf_files(files):
    all_text = ""
    for f in files:
        # Create a temp file that won't auto-delete (Windows compatibility)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(f.read())
            tmp_file_path = tmp_file.name

        try:
            loader = PyMuPDFLoader(tmp_file_path)
            docs = loader.load()
            for d in docs:
                all_text += d.page_content + "\n"
        finally:
            os.remove(tmp_file_path)  # Clean up
    return all_text
    
# Load vector store 
def load_vector_db():
    index_dir = os.path.join(settings.BASE_DIR, "vectorstores", "sample_index")
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vectorstore = FAISS.load_local(index_dir, embeddings, allow_dangerous_deserialization=True)
    return vectorstore
    
# Build RAG chain
def build_rag_chain(vectorstore):

    # Set up retriever and model
    retriever = vectorstore.as_retriever(search_type="similarity",search_kwargs={"k": 5})
    model = ChatOpenAI(model="gpt-4o", temperature=0.5)

    # Set up prompt 
    system_prompt = (
        "You are a psychologist and executive coach. Use the given context from sample psychometric assessments "
        "to analyse the client's report and provide feedback. \n\n"
        "**Always format your response using Markdown.** Use:\n"
        "- Headings for sections (`## Heading`)\n"
        "- Numbered or bulleted lists for points\n"
        "- Bold (`**`) for key phrases\n"
        "- Italics (`_`) for subtle emphasis\n"
        "- Markdown tables if needed\n"
        "- Keep paragraphs concise and break up long text\n\n"
        "Context:\n{context}"
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", "{input}"),
    ])

    # Set up chain
    question_answer_chain = create_stuff_documents_chain(model, prompt)
    chain = create_retrieval_chain(retriever, question_answer_chain)
    return chain


# Set up vector store
# Run when change PDF set to setup/update vector store based on data in RAG_data folder
@api_view(['POST'])
def setup_vector_db(request):
    data_folder = os.path.join(settings.BASE_DIR, "RAG_data") 
    all_chunks = []

    # Step 1: Chunk all PDFs
    for filename in os.listdir(data_folder):
        if filename.endswith(".pdf"):
            pdf_path = os.path.join(data_folder, filename)
            loader = PyPDFLoader(pdf_path)
            docs = loader.load()

            text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
            chunks = text_splitter.split_documents(docs)
            all_chunks.extend(chunks)

    # Step 2: Embed all chunks
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    db = FAISS.from_documents(all_chunks, embeddings)

    # Step 3: Save vectorstore
    index_dir = os.path.join(settings.BASE_DIR, "vectorstores", "sample_index")
    os.makedirs(index_dir, exist_ok=True)
    db.save_local(index_dir)

    return Response({"message": f"Indexed {len(all_chunks)} chunks from {len(os.listdir(data_folder))} PDF(s)."})