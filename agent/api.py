"""
FastAPI endpoints for the agentic RAG system.
"""

import os
import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import uvicorn
from dotenv import load_dotenv

from .agent import rag_agent, AgentDependencies
from .db_utils import (
    initialize_database,
    close_database,
    create_session,
    get_session,
    add_message,
    get_session_messages,
    get_user_sessions,
    delete_session,
    clear_session_messages,
    test_connection
)
from .graph_utils import initialize_graph, close_graph, test_graph_connection
from .models import (
    ChatRequest,
    ChatResponse,
    SearchRequest,
    SearchResponse,
    StreamDelta,
    ErrorResponse,
    HealthStatus,
    ToolCall
)
from .tools import (
    vector_search_tool,
    graph_search_tool,
    hybrid_search_tool,
    list_documents_tool,
    VectorSearchInput,
    GraphSearchInput,
    HybridSearchInput,
    DocumentListInput
)
from .json_storage import get_json_storage

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Application configuration
APP_ENV = os.getenv("APP_ENV", "development")
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", 8000))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Set debug level for our module during development
if APP_ENV == "development":
    logger.setLevel(logging.DEBUG)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI app."""
    # Startup
    logger.info("Starting up agentic RAG API...")
    
    try:
        # Initialize database connections
        await initialize_database()
        logger.info("Database initialized")
        
        # Initialize graph database
        await initialize_graph()
        logger.info("Graph database initialized")
        
        # Test connections
        db_ok = await test_connection()
        graph_ok = await test_graph_connection()
        
        if not db_ok:
            logger.error("Database connection failed")
        if not graph_ok:
            logger.error("Graph database connection failed")
        
        logger.info("Agentic RAG API startup complete")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down agentic RAG API...")
    
    try:
        await close_database()
        await close_graph()
        logger.info("Connections closed")
    except Exception as e:
        logger.error(f"Shutdown error: {e}")


# Create FastAPI app
app = FastAPI(
    title="Agentic RAG with Knowledge Graph",
    description="AI agent combining vector search and knowledge graph for tech company analysis",
    version="0.1.0",
    lifespan=lifespan
)

# Serve frontend static files (index.html) from the project's frontend directory
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND_DIR.exists():
    # Mount static assets under /static
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


# Add middleware with flexible CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.add_middleware(GZipMiddleware, minimum_size=1000)


# Helper functions for agent execution
async def get_or_create_session(request: ChatRequest) -> str:
    """Get existing session or create new one."""
    if request.session_id:
        session = await get_session(request.session_id)
        if session:
            return request.session_id
    
    # Create new session
    return await create_session(
        user_id=request.user_id,
        metadata=request.metadata
    )


async def get_conversation_context(
    user_id: str,
    max_messages: int = 10
) -> List[Dict[str, str]]:
    """
    Get recent conversation context for a user from JSON storage.
    
    Args:
        user_id: User ID (used as session identifier)
        max_messages: Maximum number of messages to retrieve
    
    Returns:
        List of messages
    """
    # Get messages from JSON storage
    json_store = get_json_storage()
    messages = json_store.get_conversation_history(user_id, limit=max_messages)
    
    return [
        {
            "role": msg["role"],
            "content": msg["content"]
        }
        for msg in messages
    ]


def extract_tool_calls(result) -> List[ToolCall]:
    """
    Extract tool calls from Pydantic AI result.
    
    Args:
        result: Pydantic AI result object
    
    Returns:
        List of ToolCall objects
    """
    tools_used = []
    
    try:
        # Get all messages from the result
        messages = result.all_messages()
        
        for message in messages:
            if hasattr(message, 'parts'):
                for part in message.parts:
                    # Check if this is a tool call part
                    if part.__class__.__name__ == 'ToolCallPart':
                        try:
                            # Debug logging to understand structure
                            logger.debug(f"ToolCallPart attributes: {dir(part)}")
                            logger.debug(f"ToolCallPart content: tool_name={getattr(part, 'tool_name', None)}")
                            
                            # Extract tool information safely
                            tool_name = str(part.tool_name) if hasattr(part, 'tool_name') else 'unknown'
                            
                            # Get args - the args field is a JSON string in Pydantic AI
                            tool_args = {}
                            if hasattr(part, 'args') and part.args is not None:
                                if isinstance(part.args, str):
                                    # Args is a JSON string, parse it
                                    try:
                                        import json
                                        tool_args = json.loads(part.args)
                                        logger.debug(f"Parsed args from JSON string: {tool_args}")
                                    except json.JSONDecodeError as e:
                                        logger.debug(f"Failed to parse args JSON: {e}")
                                        tool_args = {}
                                elif isinstance(part.args, dict):
                                    tool_args = part.args
                                    logger.debug(f"Args already a dict: {tool_args}")
                            
                            # Alternative: use args_as_dict method if available
                            if hasattr(part, 'args_as_dict'):
                                try:
                                    tool_args = part.args_as_dict()
                                    logger.debug(f"Got args from args_as_dict(): {tool_args}")
                                except:
                                    pass
                            
                            # Get tool call ID
                            tool_call_id = None
                            if hasattr(part, 'tool_call_id'):
                                tool_call_id = str(part.tool_call_id) if part.tool_call_id else None
                            
                            # Create ToolCall with explicit field mapping
                            tool_call_data = {
                                "tool_name": tool_name,
                                "args": tool_args,
                                "tool_call_id": tool_call_id
                            }
                            logger.debug(f"Creating ToolCall with data: {tool_call_data}")
                            tools_used.append(ToolCall(**tool_call_data))
                        except Exception as e:
                            logger.debug(f"Failed to parse tool call part: {e}")
                            continue
    except Exception as e:
        logger.warning(f"Failed to extract tool calls: {e}")
    
    return tools_used


async def save_conversation_turn(
    user_id: str,
    user_message: str,
    assistant_message: str,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Save a conversation turn to JSON storage by user_id.
    
    Args:
        user_id: User ID from frontend (used as session identifier)
        user_message: User's message
        assistant_message: Assistant's response
        metadata: Optional metadata
    """
    # Save ONLY to JSON storage by user_id
    try:
        json_store = get_json_storage()
        
        # Add user message to JSON (uses user_id as session_id internally)
        json_store.add_message(
            session_id=user_id,  # user_id is the session identifier now
            role="user",
            content=user_message,
            metadata=metadata
        )
        
        # Add assistant message to JSON
        json_store.add_message(
            session_id=user_id,  # user_id is the session identifier now
            role="assistant",
            content=assistant_message,
            metadata=metadata
        )
        logger.info(f"Saved conversation to JSON for user: {user_id}")
    except Exception as e:
        logger.error(f"Failed to save to JSON storage: {e}")


async def execute_agent(
    message: str,
    user_id: str,
    save_conversation: bool = True
) -> tuple[str, List[ToolCall], Optional[str]]:
    """
    Execute the agent with a message.
    
    Args:
        message: User message
        user_id: User ID (used as session identifier)
        save_conversation: Whether to save the conversation
    
    Returns:
        Tuple of (agent response, tools used)
    """
    try:
        # Create dependencies - user_id is used as session_id
        deps = AgentDependencies(
            session_id=user_id,
            user_id=user_id
        )
        
        # Get conversation context using user_id
        context = await get_conversation_context(user_id)
        logger.debug(f"Retrieved {len(context)} messages for user {user_id}")
        
        # WORKAROUND: Check if this is a compliance query and pre-search
        # (because smaller models don't reliably call tools)
        pre_search_results = None
        tools_used = []
        lower_msg = message.lower()
        
        # Detect FIX messages, greetings, and compliance/regulatory queries
        is_fix_message = "8=fix" in lower_msg and "^35=" in lower_msg
        is_greeting = lower_msg.strip() in ["hi", "hello", "hey", "thanks", "thank you", "bye"]

        # Domain keywords for securities/compliance/FIX. If none are present and it's not a FIX message,
        # treat it as out-of-domain and refuse to answer (per product policy).
        domain_keywords = [
            "rule", "rule 606", "606", "15c3", "sec", "finra", "regulation", "filing", "report", "deadline",
            "requirement", "compliance", "disclosure", "order routing", "order-routing", "execution report",
            "fix", "msgtype", "form 606", "form n-csr", "n-csr", "ncsr", "broker", "broker-dealer", "trade",
            "trade reporting", "settlement", "order", "routing", "order routing disclosure", "execution",
            "decode", "explain", "parse", "logon", "logout", "heartbeat", "execution", "cancel"
        ]

        is_compliance_query = any(kw in lower_msg for kw in domain_keywords)
        
        # SPECIAL HANDLING FOR FIX MESSAGES: Pre-process with FIX decoder
        if is_fix_message or "fix" in lower_msg and ("decode" in lower_msg or "explain" in lower_msg or "parse" in lower_msg):
            # For FIX messages, add context to the prompt
            try:
                from .fix_parser import explain_fix_message, is_fix_message as check_fix
                
                # Try to extract the FIX message from user input
                fix_msg_start = message.find("8=FIX")
                if fix_msg_start != -1:
                    # Extract FIX message (look for the message boundaries)
                    fix_msg = message[fix_msg_start:].split('\n')[0].split(' ')[0]  # Get first line/word
                    if check_fix(fix_msg):
                        # Decode the FIX message and add to context
                        fix_explanation = explain_fix_message(fix_msg)
                        full_prompt = f"""{message}

[FIX MESSAGE DECODE - PROVIDED FOR CONTEXT]
{fix_explanation}

Based on this FIX message analysis, answer the user's question about the message."""
                        logger.info(f"Pre-decoded FIX message, added explanation to prompt")
                    else:
                        full_prompt = message
                else:
                    full_prompt = message
            except Exception as e:
                logger.warning(f"FIX pre-processing failed: {e}")
                full_prompt = message
        else:
            full_prompt = message

        # SPECIAL HANDLING FOR GREETINGS: Simple, polite response
        if is_greeting:
            # For greetings, just respond naturally without forcing compliance content
            greeting_response = f"""Hi there! 👋 Thanks for saying {message}!

I'm **LawGPT**, your AI assistant for securities law, regulatory compliance, and FIX protocol questions.

Feel free to ask me anything about:
- **FINRA rules** and broker-dealer compliance
- **SEC regulations** and requirements  
- **FIX protocol** messages and trading systems
- **Order routing**, best execution, and compliance

What would you like to know?"""
            
            # Save the greeting turn for conversation history
            assistant_msg_id = None
            if save_conversation:
                assistant_msg_id = await save_conversation_turn(
                    user_id=user_id,
                    user_message=message,
                    assistant_message=greeting_response,
                    metadata={"greeting": True}
                )

            return greeting_response, [], assistant_msg_id
        
        # If the user is asking something outside the domain and it's not a FIX message or greeting, refuse.
        if not is_fix_message and not is_compliance_query:
            refusal = (
                "I can only help with securities law, regulatory compliance, and FIX protocol questions. "
                "I can't assist with that topic. If your question relates to SEC/FINRA rules, filings, or FIX messages, please rephrase."
            )
            # Save the refused conversation turn for auditability
            assistant_msg_id = None
            if save_conversation:
                assistant_msg_id = await save_conversation_turn(
                    user_id=user_id,
                    user_message=message,
                    assistant_message=refusal,
                    metadata={"refused": True}
                )

            return refusal, [], assistant_msg_id
        
        if is_compliance_query and not is_fix_message and not is_greeting:
            # Pre-fetch vector search results for compliance queries
            from .tools import vector_search_tool, VectorSearchInput
            logger.info(f"Pre-searching for compliance query: {message[:50]}...")
            search_input = VectorSearchInput(query=message, limit=5)
            search_results = await vector_search_tool(search_input)
            
            if search_results and any(r.score > 0.4 for r in search_results):
                pre_search_results = "\n\n".join([
                    f"[Source: {r.document_title}]\n{r.content[:800]}"
                    for r in search_results[:3] if r.score > 0.4
                ])
                tools_used.append(ToolCall(tool_name="vector_search", args={"query": message}))
                logger.info(f"Found {len(search_results)} relevant results for pre-search")
        
        # Build prompt with context - make it clearer for the LLM
        full_prompt = message
        if context and len(context) > 0:
            # Format conversation history more clearly
            history_lines = []
            for msg in context[-10:]:  # Last 10 messages (5 turns)
                role_label = "User" if msg['role'] == 'user' else "Assistant"
                # Truncate long messages in context
                content = msg['content'][:500] + "..." if len(msg['content']) > 500 else msg['content']
                history_lines.append(f"{role_label}: {content}")
            
            context_str = "\n".join(history_lines)
            full_prompt = f"""[CONTEXT - DO NOT REPEAT THIS IN YOUR RESPONSE]
{context_str}

[USER'S CURRENT QUESTION]
{message}

Respond ONLY to the current question above. Do NOT repeat the conversation history or include any headers like "Conversation History" or "Current Message" in your response. Start your answer directly."""
            logger.debug(f"Full prompt with context: {full_prompt[:200]}...")
        
        # Add pre-search results to prompt if available
        if pre_search_results:
            full_prompt = f"""[SEARCH RESULTS FROM DATABASE - USE THESE AS PRIMARY SOURCE]
{pre_search_results}

[USER'S QUESTION]
{message}

Answer based on the search results above. Be concise (2-4 sentences for overview, key points, practical notes)."""
        
        # Run the agent
        result = await rag_agent.run(full_prompt, deps=deps)
        
        response = result.output
        agent_tools = extract_tool_calls(result)
        tools_used.extend(agent_tools)
        
        # Save conversation if requested and return assistant message id
        assistant_msg_id = None
        if save_conversation:
            assistant_msg_id = await save_conversation_turn(
                user_id=user_id,
                user_message=message,
                assistant_message=response,
                metadata={
                    "tool_calls": len(tools_used)
                }
            )

        return response, tools_used, assistant_msg_id
        
    except Exception as e:
        logger.error(f"Agent execution failed: {e}")
        error_response = f"I encountered an error while processing your request: {str(e)}"
        
        if save_conversation:
            await save_conversation_turn(
                user_id=user_id,
                user_message=message,
                assistant_message=error_response,
                metadata={"error": str(e)}
            )

        return error_response, [], None


# API Endpoints
@app.get("/health", response_model=HealthStatus)
async def health_check():
    """Health check endpoint."""
    try:
        # Test database connections
        db_status = await test_connection()
        graph_status = await test_graph_connection()
        
        # Determine overall status
        if db_status and graph_status:
            status = "healthy"
        elif db_status or graph_status:
            status = "degraded"
        else:
            status = "unhealthy"
        
        return HealthStatus(
            status=status,
            database=db_status,
            graph_database=graph_status,
            llm_connection=True,  # Assume OK if we can respond
            version="0.1.0",
            timestamp=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")


# Session management endpoints for frontend
@app.post("/sessions")
async def list_sessions(request: Request):
    """List all sessions for a user."""
    try:
        body = await request.json()
        user_id = body.get("user_id", "anonymous")
        
        sessions = await get_user_sessions(user_id)
        return {"sessions": sessions}
        
    except Exception as e:
        logger.error(f"List sessions failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/init_chat")
async def init_chat(request: Request):
    """Initialize a chat session - returns greeting or existing messages."""
    try:
        body = await request.json()
        user_id = body.get("user_id", "anonymous")
        session_id = body.get("session_id")
        
        # If session_id provided, load existing messages
        if session_id:
            session = await get_session(session_id)
            if session:
                messages = await get_session_messages(session_id)
                chats = [
                    {
                        "role": msg["role"],
                        "content": msg["content"],
                        "message_id": msg["id"]
                    }
                    for msg in messages
                ]
                return {
                    "session_id": session_id,
                    "chats": chats
                }
        
        # Create new session
        new_session_id = await create_session(user_id=user_id)
        
        # Add greeting message
        greeting = """Hi, welcome to LawGPT! 👋

I'm your AI assistant specializing in securities and financial law. I can help you with:

**FINRA Rules & Regulations** - Compliance requirements, trading practices, broker-dealer obligations

**SEC Compliance** - SEC rules, form filings, regulatory requirements like Rule 606, Rule 10b-5

**FIX Protocol** - Decode FIX messages, explain message types and tags, trading system integration

**Order Routing & Execution** - Best execution practices, order handling, routing disclosure

Feel free to ask me any questions about securities law, compliance, regulations, or FIX protocol. What would you like to know?"""
        # Save greeting into both DB and JSON storage so frontend feedback works
        try:
            db_msg_id = await add_message(
                session_id=new_session_id,
                role="assistant",
                content=greeting
            )
        except Exception:
            db_msg_id = None

        # Also save into JSON storage (user-based file) and get stable message id
        try:
            json_store = get_json_storage()
            json_msg_id = json_store.add_message(
                session_id=user_id,
                role="assistant",
                content=greeting
            )
        except Exception:
            json_msg_id = None

        return {
            "session_id": new_session_id,
            "greeting": greeting,
            "greeting_id": json_msg_id or db_msg_id
        }
        
    except Exception as e:
        logger.error(f"Init chat failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/delete_chats")
async def delete_chats(request: Request):
    """Delete a chat session."""
    try:
        body = await request.json()
        user_id = body.get("user_id", "anonymous")
        session_id = body.get("session_id")
        
        if not session_id:
            raise HTTPException(status_code=400, detail="session_id required")
        
        success = await delete_session(session_id, user_id)
        return {"success": success}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete chats failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/clear_history")
async def clear_history(request: Request):
    """Clear messages from a session but keep the session."""
    try:
        body = await request.json()
        session_id = body.get("session_id")
        
        if not session_id:
            raise HTTPException(status_code=400, detail="session_id required")
        
        success = await clear_session_messages(session_id)
        return {"success": success}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Clear history failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/feedback")
async def submit_feedback(request: Request):
    """Submit feedback (like/dislike/comment) for a specific message.

    Expected JSON body:
    {
        "user_id": "user_001",
        "session_id": "user_001",
        "message_id": "...",
        "feedback_type": "like|dislike|comment",
        "comment": "optional comment"
    }
    """
    try:
        body = await request.json()
        user_id = body.get("user_id") or "anonymous"
        session_id = body.get("session_id") or user_id
        message_id = body.get("message_id")
        feedback_type = body.get("feedback_type")
        comment = body.get("comment")

        if not message_id or not feedback_type:
            raise HTTPException(status_code=400, detail="message_id and feedback_type are required")

        storage = get_json_storage()
        saved = storage.add_feedback(
            session_id=session_id,
            message_id=message_id,
            feedback_type=feedback_type,
            comment=comment,
            actor_id=user_id
        )

        if not saved:
            raise HTTPException(status_code=404, detail="Message or user not found")

        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Feedback submission failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Non-streaming chat endpoint."""
    try:
        # Use session_id if provided (for conversation continuity), otherwise use user_id
        user_id = request.session_id or request.user_id or "anonymous"
        
        # Execute agent with user_id (which may be session_id or user_id depending on context)
        response, tools_used, assistant_msg_id = await execute_agent(
            message=request.message,
            user_id=user_id
        )

        return ChatResponse(
            message=response,
            session_id=user_id,  # Return the actual session_id that was used
            tools_used=tools_used,
            assistant_message_id=assistant_msg_id,
            metadata={"search_type": str(request.search_type)}
        )
        
    except Exception as e:
        logger.error(f"Chat endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Streaming chat endpoint using Server-Sent Events."""
    try:
        # Get or create session
        session_id = await get_or_create_session(request)
        
        async def generate_stream():
            """Generate streaming response using agent.iter() pattern."""
            try:
                yield f"data: {json.dumps({'type': 'session', 'session_id': session_id})}\n\n"
                
                # Create dependencies
                deps = AgentDependencies(
                    session_id=session_id,
                    user_id=request.user_id
                )
                
                # Get conversation context
                context = await get_conversation_context(session_id)
                
                # Build input with context
                full_prompt = request.message
                if context:
                    context_str = "\n".join([
                        f"{msg['role']}: {msg['content']}"
                        for msg in context[-6:]
                    ])
                    full_prompt = f"Previous conversation:\n{context_str}\n\nCurrent question: {request.message}"
                
                # Save user message immediately
                await add_message(
                    session_id=session_id,
                    role="user",
                    content=request.message,
                    metadata={"user_id": request.user_id}
                )
                
                full_response = ""
                
                # Stream using agent.iter() pattern
                async with rag_agent.iter(full_prompt, deps=deps) as run:
                    async for node in run:
                        if rag_agent.is_model_request_node(node):
                            # Stream tokens from the model
                            async with node.stream(run.ctx) as request_stream:
                                async for event in request_stream:
                                    from pydantic_ai.messages import PartStartEvent, PartDeltaEvent, TextPartDelta
                                    
                                    if isinstance(event, PartStartEvent) and event.part.part_kind == 'text':
                                        delta_content = event.part.content
                                        yield f"data: {json.dumps({'type': 'text', 'content': delta_content})}\n\n"
                                        full_response += delta_content
                                        
                                    elif isinstance(event, PartDeltaEvent) and isinstance(event.delta, TextPartDelta):
                                        delta_content = event.delta.content_delta
                                        yield f"data: {json.dumps({'type': 'text', 'content': delta_content})}\n\n"
                                        full_response += delta_content
                
                # Extract tools used from the final result
                result = run.result
                tools_used = extract_tool_calls(result)
                
                # Send tools used information
                if tools_used:
                    tools_data = [
                        {
                            "tool_name": tool.tool_name,
                            "args": tool.args,
                            "tool_call_id": tool.tool_call_id
                        }
                        for tool in tools_used
                    ]
                    yield f"data: {json.dumps({'type': 'tools', 'tools': tools_data})}\n\n"
                
                # Save assistant response
                assistant_msg_id = await add_message(
                    session_id=session_id,
                    role="assistant",
                    content=full_response,
                    metadata={
                        "streamed": True,
                        "tool_calls": len(tools_used)
                    }
                )

                # Send assistant message id so frontend can update ephemeral ids
                yield f"data: {json.dumps({'type': 'assistant_message_id', 'assistant_message_id': assistant_msg_id})}\n\n"
                yield f"data: {json.dumps({'type': 'end'})}\n\n"
                
            except Exception as e:
                logger.error(f"Stream error: {e}")
                error_chunk = {
                    "type": "error",
                    "content": f"Stream error: {str(e)}"
                }
                yield f"data: {json.dumps(error_chunk)}\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )
        
    except Exception as e:
        logger.error(f"Streaming chat failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search/vector")
async def search_vector(request: SearchRequest):
    """Vector search endpoint."""
    try:
        input_data = VectorSearchInput(
            query=request.query,
            limit=request.limit
        )
        
        start_time = datetime.now()
        results = await vector_search_tool(input_data)
        end_time = datetime.now()
        
        query_time = (end_time - start_time).total_seconds() * 1000
        
        return SearchResponse(
            results=results,
            total_results=len(results),
            search_type="vector",
            query_time_ms=query_time
        )
        
    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search/graph")
async def search_graph(request: SearchRequest):
    """Knowledge graph search endpoint."""
    try:
        input_data = GraphSearchInput(
            query=request.query
        )
        
        start_time = datetime.now()
        results = await graph_search_tool(input_data)
        end_time = datetime.now()
        
        query_time = (end_time - start_time).total_seconds() * 1000
        
        return SearchResponse(
            graph_results=results,
            total_results=len(results),
            search_type="graph",
            query_time_ms=query_time
        )
        
    except Exception as e:
        logger.error(f"Graph search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search/hybrid")
async def search_hybrid(request: SearchRequest):
    """Hybrid search endpoint."""
    try:
        input_data = HybridSearchInput(
            query=request.query,
            limit=request.limit
        )
        
        start_time = datetime.now()
        results = await hybrid_search_tool(input_data)
        end_time = datetime.now()
        
        query_time = (end_time - start_time).total_seconds() * 1000
        
        return SearchResponse(
            results=results,
            total_results=len(results),
            search_type="hybrid",
            query_time_ms=query_time
        )
        
    except Exception as e:
        logger.error(f"Hybrid search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents")
async def list_documents_endpoint(
    limit: int = 20,
    offset: int = 0
):
    """List documents endpoint."""
    try:
        input_data = DocumentListInput(limit=limit, offset=offset)
        documents = await list_documents_tool(input_data)
        
        return {
            "documents": documents,
            "total": len(documents),
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"Document listing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sessions/{session_id}")
async def get_session_info(session_id: str):
    """Get session information."""
    try:
        session = await get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return session
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Serve the frontend index at the root path (if frontend exists)
@app.get("/", include_in_schema=False)
async def serve_frontend_index():
    try:
        index_path = FRONTEND_DIR / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        # If no frontend, show a small JSON message
        return {"message": "API is running. No frontend detected."}
    except Exception as e:
        logger.error(f"Error serving frontend index: {e}")
        raise HTTPException(status_code=500, detail="Failed to serve frontend")


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}")
    
    return ErrorResponse(
        error=str(exc),
        error_type=type(exc).__name__,
        request_id=str(uuid.uuid4())
    )


# Development server
if __name__ == "__main__":
    uvicorn.run(
        "agent.api:app",
        host=APP_HOST,
        port=APP_PORT,
        reload=APP_ENV == "development",
        log_level=LOG_LEVEL.lower()
    )