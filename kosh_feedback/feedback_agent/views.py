import os
import tempfile
import traceback
import uuid 
import json

from typing import TypedDict, Annotated, Sequence, Optional

from django.shortcuts import render
from django.conf import settings

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .serializers import *
from .models import *

# To generate PDF ##
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_JUSTIFY

# Reducer function to manage state
from operator import add as add_messages ##

# Setup Vector DB and RAG stuff
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.document_loaders import PyMuPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool

# Langgraph
from langgraph.graph import StateGraph, START, END
# from langgraph.graph.message import add_messages # Reducer to append messages
from langgraph.prebuilt import ToolNode

# Env
from dotenv import load_dotenv 
load_dotenv()

#################### Helper functions ######################

# Load vector store 
def load_vector_db():
    index_dir = os.path.join(settings.BASE_DIR, "vectorstores", "sample_index")
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vectorstore = FAISS.load_local(index_dir, embeddings, allow_dangerous_deserialization=True)
    return vectorstore

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

# Set up vector store - Run to process RAG data into vector store
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


# --- LangGraph Agent Setup ---

class State(TypedDict):
    """Store state values here"""
    messages: Annotated[Sequence[BaseMessage], add_messages] # List of messages
    user_report_content: Optional[str] # To store the user's uploaded report text

llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
retriever = load_vector_db()

#################################
# Tool definition
@tool
def pdf_tool(summary_content: str) -> str:
    """
    Generates a PDF summary from the provided content.
    The 'summary_content' argument should be the complete text for the PDF,
    including analysis of the user's report, conversation summary, and next steps.
    """
    unique_id = uuid.uuid4() 
    # Create a unique filename for the PDF
    pdf_filename = f"career_coach_summary_{unique_id}.pdf"
    
    pdf_output_dir = os.path.join(settings.MEDIA_ROOT, "generated_pdfs")
    os.makedirs(pdf_output_dir, exist_ok=True) # Ensure directory exists
    pdf_filepath = os.path.join(pdf_output_dir, pdf_filename)

    try:
        doc = SimpleDocTemplate(pdf_filepath, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph("<b>Kosh Feedback Session Summary</b>", styles['h1']))
        story.append(Spacer(1, 0.2 * inch))

        formatted_summary = summary_content.replace('\n', '<br/>')
        story.append(Paragraph(formatted_summary, styles['Normal']))
        story.append(Spacer(1, 0.2 * inch))

        doc.build(story)

        # Construct the URL to the PDF. This assumes MEDIA_URL is correctly set
        # and your web server (or Django dev server) is serving files from MEDIA_ROOT
        pdf_url = f"{settings.MEDIA_URL}generated_pdfs/{pdf_filename}"
        return f'{{"status": "success", "message": "PDF summary successfully generated.", "url": "{pdf_url}", "filename": "{pdf_filename}"}}'

    except Exception as e:
        print(f"Error generating PDF: {e}")
        return f'{{"status": "error", "message": "Failed to generate PDF summary: {str(e)}", "url": null, "filename": null}}'

@tool
def retriever_tool(query: str) -> str:
    """This tool searches and returns the information from our vectorstore of research."""
    docs = retriever.invoke(query)

    if not docs:
        return "I found no relevant information in the vectorstore"
    
    results = []
    for i, doc in enumerate(docs):
        results.append(f"Document {i+1}:\n{doc.page_content}")
    
    return "\n\n".join(results)

tools = [pdf_tool, retriever_tool]
tools_dict = {our_tool.name: our_tool for our_tool in tools} # Creating a dictionary of our tools

################################
# Node definition
llm = llm.bind_tools(tools) # Enables tool calling

def should_continue(state: State):
    """Check if the last message contains tool calls"""
    result = state['messages'][-1]
    return hasattr(result, 'tool_calls') and len(result.tool_calls) > 0

def tool_agent(state: State) -> State:
    """Execute tool calls from the LLM's response."""
    tool_calls = state['messages'][-1].tool_calls
    results = []
    for t in tool_calls:

        if t['name'] == 'pdf_tool':
            # The LLM should have provided 'summary_content' in its args for the PDF tool
            summary_content = t['args'].get('summary_content', '')
            if not summary_content:
                result = "Error: PDF tool called but no 'summary_content' provided by the LLM."
            else:
                result = tools_dict[t['name']].invoke(summary_content) # Invoke with the generated content
        elif t['name'] == 'retriever_tool':
            result = tools_dict[t['name']].invoke(t['args'].get('query', ''))
        else:
            # Handle cases where the LLM tries to call an unknown tool
            result = f"Unknown tool: {t['name']}. Please ensure only available tools are used. Arguments provided: {t['args']}"
        
        results.append(ToolMessage(tool_call_id=t['id'], name=t['name'], content=str(result)))

    print("Tools Execution Complete. Back to the model!")
    return {'messages': results} # This returns the ToolMessage(s) to the state

def llm_call(state:State) -> State:
    # Updated system prompt to guide the LLM on tool usage and content generation
    system_prompt_content = (
        "You are a compassionate and insightful career coach. Your primary goal is to provide "
        "comprehensive, detailed and verbose analysis and actionable guidance based on the client's psychometric reports "
        "and our conversation.\n\n"
        "**Context for Analysis:**\n"
        "- Use the `retriever_tool` to access information from our pool of research resources when needed. "
        "  Provide a precise search `query` to this tool.\n"
        "- The client's uploaded psychometric report content is available to you. "
        "  Integrate insights from this 'User Report Content' into your analysis.\n\n"
        "**Tool Usage Guidelines:**\n"
        "- If the client asks to **end the session**, **generate a summary**, or requests a **PDF of the session/report**, "
        "  you **must** use the `pdf_tool`.\n"
        "- When calling the `pdf_tool`, you **must** provide the *entire summary content* as the `summary_content` argument. "
        "  This `summary_content` should be a comprehensive text that includes:\n"
        "    1.  An in-depth analysis of the user's psychometric reports, elaborating on strengths and weaknesses.\n"
        "    2.  A detailed and long summary of the entire conversation up to this point.\n"
        "    3.  Clear, actionable recommendations for the user's immediate next steps in their career journey.\n"
        "    Ensure this summary is well-formatted and ready for PDF generation.\n\n"
        "**Response Formatting:**\n"
        "- Always format your direct responses using Markdown, compatible with <ReactMarkdown>.\n"
        "- Provide an in-depth analysis, elaborating on each major sub-point with clear, detailed explanations.\n"
        "- Offer clear, actionable, and empathetic advice.\n"
        "- **Crucially, cite specific parts of the retrieved documents (e.g., 'According to Document 3...') when using information from the `retriever_tool`.**\n"
        "Your final answer should be a well-structured, thorough, verbose and comprehensive and helpful Markdown response to the client, or a tool call."
    )
    system_message = SystemMessage(content=system_prompt_content)
    
    # Prepare messages for LLM, including system prompt and user_report_content if present
    messages_for_llm = [system_message]
    
    # Inject user's report content as a SystemMessage if available in the state
    if state.get("user_report_content"):
        messages_for_llm.append(SystemMessage(content=f"--- Client's Psychometric Report ---\n{state['user_report_content']}\n--- End Client's Psychometric Report ---"))

    messages_for_llm.extend(list(state["messages"])) # Add the actual conversation history
    
    response = llm.invoke(messages_for_llm) # Use the correctly named bound LLM instance
    
    return {"messages": [response]} # Updates the state via add_messages

################################
# State Graph
graph = StateGraph(State)

graph.add_node("llm_call", llm_call)
graph.add_node("tool_agent", tool_agent)

graph.add_conditional_edges(
    "llm_call",
    should_continue,
    {True: "tool_agent", False: END}
)

graph.add_edge("tool_agent", "llm_call")
graph.set_entry_point("llm_call")

app = graph.compile()

################################
# Invocation / API call

@api_view(['POST'])
def query_chatgpt(request):
    user_question = request.POST.get("message") # User's current text message/query
    files = request.FILES.getlist("files")     # List of uploaded PDF files

    user_doc_text = ""
    if files: # Only process if files are uploaded
        user_doc_text = process_pdf_files(files)

    messages = [HumanMessage(content=user_question)]

    initial_state = {
        "messages": messages,
        "user_report_content": user_doc_text if user_doc_text else None
    }

    try:
        result = app.invoke(initial_state)
        final_message_content = result["messages"][-1].content

        pdf_status_data = None # Store parsed JSON data here
        # Iterate through messages to find the PDF tool's output
        for msg in reversed(result["messages"]):
            if isinstance(msg, ToolMessage) and msg.name == "pdf_tool":
                try:
                    # Parse the JSON string returned by the pdf_tool
                    pdf_status_data = json.loads(msg.content)
                except json.JSONDecodeError:
                    pdf_status_data = {"status": "error", "message": msg.content}
                break

        response_data = {"response": final_message_content}
        if pdf_status_data:
            response_data["pdf_info"] = pdf_status_data # Add the parsed dictionary
        return Response(response_data)

    except Exception as e:
        print(traceback.format_exc()) # Print full traceback
        return Response({"error": str(e)}, status=500)


