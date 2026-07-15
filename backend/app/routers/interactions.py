"""
API Routes for HCP Interactions
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models import Interaction, HCP
from app.schemas import (
    Interaction as InteractionSchema,
    InteractionCreate,
    InteractionUpdate,
    ChatMessage,
    ChatResponse,
    HCP as HCPSchema,
)
from local_langgraph.agent import get_agent
from local_langgraph.tools import InteractionTools
from local_langgraph.orchestrator import get_orchestrator

router = APIRouter(prefix="/interactions", tags=["interactions"])


@router.get("", response_model=List[InteractionSchema])
async def list_interactions(
    limit: int = 50,
    hcp_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """List interactions, optionally filtered by HCP."""
    query = db.query(Interaction).order_by(Interaction.date.desc())

    if hcp_id is not None:
        hcp = db.query(HCP).filter(HCP.id == hcp_id).first()
        if not hcp:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"HCP with id {hcp_id} not found",
            )
        query = query.filter(Interaction.hcp_id == hcp_id)

    interactions = query.limit(limit).all()
    
    # Attach HCP names to interactions
    result = []
    for interaction in interactions:
        hcp = db.query(HCP).filter(HCP.id == interaction.hcp_id).first()
        interaction_dict = {
            "id": interaction.id,
            "hcp_id": interaction.hcp_id,
            "hcp_name": hcp.name if hcp else f"HCP #{interaction.hcp_id}",
            "interaction_type": interaction.interaction_type,
            "date": interaction.date,
            "time": interaction.time,
            "attendees": interaction.attendees,
            "topics_discussed": interaction.topics_discussed,
            "ai_summary": interaction.ai_summary,
            "sentiment": interaction.sentiment,
            "key_entities": interaction.key_entities,
            "outcomes": interaction.outcomes,
            "follow_up_actions": interaction.follow_up_actions,
            "materials_shared": interaction.materials_shared,
            "samples_distributed": interaction.samples_distributed,
            "created_at": interaction.created_at,
            "updated_at": interaction.updated_at,
        }
        result.append(interaction_dict)
    
    return result


@router.post("/log", response_model=InteractionSchema)
async def log_interaction(
    interaction: InteractionCreate,
    db: Session = Depends(get_db),
):
    """
    Log a new HCP interaction using structured form or AI processing.

    This endpoint:
    1. Accepts interaction details
    2. Uses Groq LLM to summarize and extract entities
    3. Stores in database
    4. Returns saved interaction with AI-generated insights
    """
    try:
        # Verify HCP exists
        hcp = db.query(HCP).filter(HCP.id == interaction.hcp_id).first()
        if not hcp:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"HCP with id {interaction.hcp_id} not found",
            )

        # Use tool to log interaction
        result = InteractionTools.log_interaction(
            hcp_id=interaction.hcp_id,
            interaction_type=interaction.interaction_type.value,
            date=interaction.date.isoformat(),
            time=interaction.time,
            attendees=interaction.attendees,
            topics_discussed=interaction.topics_discussed,
            raw_text=interaction.raw_text,
            outcomes=interaction.outcomes,
            follow_up_actions=interaction.follow_up_actions,
            db=db,
        )

        if result["status"] == "error":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"],
            )

        # Return the created interaction
        interaction_obj = db.query(Interaction).filter(
            Interaction.id == result["interaction_id"]
        ).first()

        return interaction_obj

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error logging interaction: {str(e)}",
        )


@router.get("/hcp/{hcp_id}", response_model=List[InteractionSchema])
async def get_hcp_interactions(
    hcp_id: int,
    limit: int = 10,
    db: Session = Depends(get_db),
):
    """Get all interactions for a specific HCP"""
    # Verify HCP exists
    hcp = db.query(HCP).filter(HCP.id == hcp_id).first()
    if not hcp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"HCP with id {hcp_id} not found",
        )

    interactions = (
        db.query(Interaction)
        .filter(Interaction.hcp_id == hcp_id)
        .order_by(Interaction.date.desc())
        .limit(limit)
        .all()
    )

    return interactions


@router.get("/hcps", response_model=List[HCPSchema])
async def list_hcps(
    db: Session = Depends(get_db),
):
    """List all Healthcare Professionals for selection."""
    hcps = db.query(HCP).order_by(HCP.name.asc()).all()
    return hcps


@router.get("/{interaction_id}", response_model=InteractionSchema)
async def get_interaction(
    interaction_id: int,
    db: Session = Depends(get_db),
):
    """Get a specific interaction by ID"""
    interaction = db.query(Interaction).filter(
        Interaction.id == interaction_id
    ).first()

    if not interaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interaction {interaction_id} not found",
        )

    return interaction


@router.put("/{interaction_id}", response_model=InteractionSchema)
async def edit_interaction(
    interaction_id: int,
    updates: InteractionUpdate,
    db: Session = Depends(get_db),
):
    """
    Edit an existing interaction.

    This endpoint uses the LangGraph "edit_interaction" tool to:
    1. Validate the interaction exists
    2. Apply updates
    3. Regenerate AI summary if content changed
    4. Return updated interaction
    """
    # Verify interaction exists
    interaction = db.query(Interaction).filter(
        Interaction.id == interaction_id
    ).first()

    if not interaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interaction {interaction_id} not found",
        )

    try:
        # Use tool to edit interaction
        updates_dict = updates.model_dump(exclude_unset=True)
        result = InteractionTools.edit_interaction(
            interaction_id=interaction_id,
            updates=updates_dict,
            db=db,
        )

        if result["status"] == "error":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"],
            )

        # Return updated interaction
        interaction = db.query(Interaction).filter(
            Interaction.id == interaction_id
        ).first()

        return interaction

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error editing interaction: {str(e)}",
        )


@router.delete("/{interaction_id}")
async def delete_interaction(
    interaction_id: int,
    db: Session = Depends(get_db),
):
    """Delete an interaction"""
    interaction = db.query(Interaction).filter(
        Interaction.id == interaction_id
    ).first()

    if not interaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interaction {interaction_id} not found",
        )

    db.delete(interaction)
    db.commit()

    return {"message": f"Interaction {interaction_id} deleted successfully"}


@router.post("/chat", response_model=ChatResponse)
async def chat_with_agent(
    message: ChatMessage,
    db: Session = Depends(get_db),
):
    """
    Chat interface for logging interactions using conversational AI.

    This endpoint:
    1. Accepts user message
    2. Uses LangGraph agent to understand intent
    3. Routes to appropriate tool (log, edit, search, etc.)
    4. Returns AI response with suggested tools
    """
    try:
        agent = get_agent()

        # FIX: Use user_id as session_id for persistent context across messages
        session_id = message.user_id or "default"

        # Process message through agent
        result = agent.process_interaction(
            user_message=message.message,
            interaction_context=message.interaction_data,
            db=db,
            session_id=session_id,
        )

        if result["status"] == "error":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"],
            )

        # Extract response - handle multiple response formats from different handlers
        tool_result = result.get("result", {})
        response_message = (
            tool_result.get("response", "")
            or tool_result.get("message", "")
            or tool_result.get("full_response", "")
            or (tool_result.get("suggestions") and "\n".join(tool_result["suggestions"]))
            or str(tool_result.get("extracted", {}))
        )

        return ChatResponse(
            response=response_message,
            suggested_tools=[result.get("intent", "general")],
            interaction_id=tool_result.get("interaction_id"),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing chat: {str(e)}",
        )


@router.post("/orchestrate")
async def orchestrate_tools(
    message: ChatMessage,
    db: Session = Depends(get_db),
):
    """
    LangGraph orchestration endpoint.
    Takes a user message, extracts structured data, and executes the appropriate tools.

    This endpoint:
    1. Extracts structured data from the message
    2. Detects intent (log, search, history, etc.)
    3. Executes primary tool
    4. Executes secondary tools (follow-ups, materials)
    5. Returns aggregated results
    """
    try:
        from app.routers.extraction import extract_form_data
        from app.schemas import ExtractionRequest

        # Step 1: Extract structured data
        extraction_request = ExtractionRequest(
            message=message.message,
            hcp_context=message.interaction_data,
        )
        extraction_result = await extract_form_data(extraction_request)

        # Step 2: Orchestrate tool execution
        orchestrator = get_orchestrator(db)
        extraction_dict = extraction_result.model_dump()
        orchestration_result = orchestrator.orchestrate(
            extraction=extraction_dict,
            message=message.message,
        )

        return {
            "status": "success",
            "extraction": extraction_dict,
            "orchestration": orchestration_result,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error in orchestration: {str(e)}",
        )


@router.post("/search")
async def search_hcp(
    query: str,
    search_type: str = "name",
    db: Session = Depends(get_db),
):
    """
    Search for Healthcare Professionals using the search_hcp tool.

    Args:
        query: Search query string
        search_type: Type of search (name, specialty, organization)
    """
    try:
        result = InteractionTools.search_hcp(
            query=query,
            search_type=search_type,
            db=db,
        )

        return result

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching HCPs: {str(e)}",
        )


@router.post("/follow-up/{interaction_id}")
async def get_follow_up_suggestions(
    interaction_id: int,
    db: Session = Depends(get_db),
):
    """
    Get AI-suggested follow-up actions for an interaction.

    This uses the suggest_follow_up_actions tool to:
    1. Retrieve the interaction
    2. Analyze its content
    3. Generate actionable follow-up suggestions
    """
    try:
        result = InteractionTools.suggest_follow_up_actions(
            interaction_id=interaction_id,
            db=db,
        )

        if result["status"] == "error":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"],
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting follow-up suggestions: {str(e)}",
        )


@router.get("/recommendations/{topic}")
async def get_material_recommendations(
    topic: str,
    db: Session = Depends(get_db),
):
    """
    Get recommended materials for a topic using the get_recommended_materials tool.

    Args:
        topic: Topic or disease area to find materials for
    """
    try:
        result = InteractionTools.get_recommended_materials(
            topic=topic,
            db=db,
        )

        return result

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting recommendations: {str(e)}",
        )
