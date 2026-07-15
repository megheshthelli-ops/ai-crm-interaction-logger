# AI-First CRM HCP Module – Log Interaction Screen

A comprehensive Healthcare Professional (HCP) Customer Relationship Management system with AI-powered interaction logging capabilities.

## 🎯 Project Overview

This project implements an **AI-First CRM system** for field representatives in the life sciences industry to log and manage interactions with healthcare professionals. The system provides two flexible interfaces:

1. **Structured Form Interface** - For detailed, organized interaction logging
2. **Conversational AI Chat Interface** - For natural language interaction description

### Key Features

- **LLM-Powered Summarization**: Uses Groq (gemma2-9b-it) LLM to automatically summarize interactions
- **Entity Extraction**: AI-powered extraction of key entities (names, medications, diseases, etc.)
- **Sentiment Analysis**: Automatic sentiment detection of interactions
- **5+ LangGraph Tools**: Comprehensive toolset for managing HCP interactions
- **Interaction History**: Complete audit trail of all HCP interactions
- **Follow-up Suggestions**: AI-generated follow-up actions
- **Material Recommendations**: Smart suggestions for relevant materials to share

## 🏗️ Technology Stack

### Backend
- **Framework**: FastAPI (Python)
- **Database**: PostgreSQL/MySQL with SQLAlchemy ORM
- **AI/ML**:
  - **LangGraph**: For agent orchestration and tool management
  - **Groq LLM**: gemma2-9b-it model for AI processing
  - **LangChain**: For LLM integration
- **API**: RESTful API with async support

### Frontend
- **Framework**: React 19 with Vite
- **State Management**: Redux Toolkit
- **UI Components**: Material-UI (MUI)
- **Styling**: CSS with Google Inter font
- **HTTP Client**: Axios

## 📋 Core Features & LangGraph Tools

### 5+ Mandatory Tools

1. **log_interaction** ✅
   - Captures interaction data with HCP
   - Uses LLM for automatic summarization
   - Extracts key entities and sentiment
   - Stores in database

2. **edit_interaction** ✅
   - Modifies previously logged interactions
   - Regenerates summaries if content changes
   - Maintains audit trail

3. **search_hcp** ✅
   - Searches HCPs by name, specialty, or organization
   - Returns matching professionals

4. **get_interaction_history** ✅
   - Retrieves all past interactions with specific HCP
   - Ordered by recency

5. **suggest_follow_up_actions** ✅
   - AI-powered follow-up suggestions
   - Based on interaction content and outcomes

6. **get_recommended_materials** ✅
   - Suggests relevant materials/samples
   - Based on discussion topics

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- Node.js 16+
- PostgreSQL 12+ OR MySQL 8+
- Groq API Key (free at https://console.groq.com)

### Backend Setup

#### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

#### 2. Configure Database
Create a `.env` file in the `backend` directory:
```env
# Database Configuration
DATABASE_URL=postgresql://postgres:password@localhost:5432/ai_crm_hcp

# For MySQL:
# DATABASE_URL=mysql+pymysql://user:password@localhost:3306/ai_crm_hcp

# Groq API Configuration
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=gemma2-9b-it

# CORS Configuration
CORS_ORIGINS=http://localhost:5173,http://localhost:3000,http://localhost:8080

# Debug Mode
DEBUG=True
```

#### 3. Initialize Database
```bash
python -c "from app.database import init_db; init_db()"
```

#### 4. Run Backend Server
```bash
uvicorn app.main:app --reload --port 8000
```

Backend will be available at: `http://localhost:8000`
API Documentation: `http://localhost:8000/docs`

### Frontend Setup

#### 1. Install Dependencies
```bash
cd frontend
npm install
```

#### 2. Configure API URL (Optional)
Create a `.env` file in the `frontend` directory:
```env
REACT_APP_API_URL=http://localhost:8000
```

#### 3. Run Development Server
```bash
npm run dev
```

Frontend will be available at: `http://localhost:5173`

## 📊 Project Structure

```
ai-first-crm-hcp-module/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI application
│   │   ├── database.py             # Database configuration
│   │   ├── models.py               # SQLAlchemy models
│   │   ├── schemas.py              # Pydantic schemas
│   │   └── routers/
│   │       └── interactions.py     # API endpoints
│   ├── langgraph/
│   │   ├── agent.py                # LangGraph agent
│   │   └── tools.py                # Tool definitions (6 tools)
│   ├── services/
│   │   └── groq_service.py         # Groq LLM integration
│   ├── requirements.txt
│   ├── .env                        # Environment variables
│   └── main.py                     # Entry point
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── AIChat.jsx          # Conversational interface
│   │   │   ├── InteractionForm.jsx # Structured form
│   │   │   ├── HistoryTable.jsx    # Interaction history
│   │   │   ├── Navbar.jsx          # Navigation bar
│   │   │   └── Sidebar.jsx         # Sidebar navigation
│   │   ├── store/
│   │   │   ├── index.js            # Redux store
│   │   │   └── slices/
│   │   │       ├── interactionSlice.js
│   │   │       ├── hcpSlice.js
│   │   │       └── chatSlice.js
│   │   ├── services/
│   │   │   └── api.js              # API client
│   │   ├── App.jsx                 # Main app component
│   │   ├── main.jsx                # Entry point
│   │   └── index.css               # Global styles
│   ├── package.json
│   ├── vite.config.js
│   └── index.html
│
├── docs/                           # Documentation
├── README.md
└── LICENSE
```

## 🔌 API Endpoints

### Interactions
- `POST /interactions/log` - Log new interaction
- `GET /interactions/{id}` - Get interaction by ID
- `GET /interactions/hcp/{hcp_id}` - Get HCP's interaction history
- `PUT /interactions/{id}` - Edit interaction
- `DELETE /interactions/{id}` - Delete interaction
- `POST /interactions/chat` - Chat with AI assistant
- `POST /interactions/search` - Search HCPs
- `POST /interactions/follow-up/{id}` - Get follow-up suggestions
- `GET /interactions/recommendations/{topic}` - Get material recommendations

## 🧠 LangGraph Agent Architecture

The agent manages HCP interactions through an orchestrated workflow:

```
User Input
    ↓
Intent Analysis (LLM)
    ↓
Tool Router (LangGraph)
    ├── log_interaction
    ├── edit_interaction
    ├── search_hcp
    ├── get_interaction_history
    ├── suggest_follow_up_actions
    └── get_recommended_materials
    ↓
Tool Execution
    ↓
Response Generation (LLM)
    ↓
User Response
```

## 🎨 Frontend Interfaces

### Tab 1: Structured Form Interface
- Dropdown for HCP selection
- Date/time picker
- Text fields for attendees and topics
- Auto-summarization via AI

### Tab 2: AI Chat Assistant
- Natural language input
- Real-time chat interface
- Automatic interaction extraction
- Suggested tool recommendations

### Tab 3: Interaction History
- Table view of all interactions
- Filter by HCP
- Edit/delete capabilities
- View AI-generated summaries

## 🔐 Key Implementation Details

### Database Models
- **HCP**: Healthcare Professional information
- **Interaction**: Detailed interaction records
- **Material**: Available materials/samples
- **FollowUpTask**: Tracking follow-up actions

### State Management (Redux)
- `interactions` - Manage interactions and current selection
- `hcps` - Store and search HCP data
- `chat` - Handle chat messages and AI responses

### Error Handling
- Comprehensive try-catch blocks
- User-friendly error messages
- Fallback responses from AI
- Database transaction management

## 📝 Usage Examples

### Via Form Interface
1. Select HCP from dropdown
2. Choose interaction type
3. Set date and time
4. Enter attendees and topics
5. Click "Log Interaction"
6. AI automatically summarizes

### Via Chat Interface
1. "I met with Dr. Smith today for 30 minutes..."
2. "We discussed cardiac medications and recent clinical trials..."
3. AI extracts details and suggests follow-ups
4. Review and confirm

## 🔒 Security Considerations

- Environment variables for sensitive data
- CORS configuration
- Input validation with Pydantic
- SQL injection prevention via ORM
- Error messages don't expose system details

## 🐛 Troubleshooting

### Backend Won't Start
```bash
# Check Python version
python --version  # Should be 3.8+

# Verify database connection
pip list | grep sqlalchemy

# Check Groq API key
echo $GROQ_API_KEY
```

### Frontend Connection Issues
- Verify backend is running on port 8000
- Check CORS_ORIGINS in backend .env
- Clear browser cache
- Check browser console for errors

### Database Issues
```bash
# Reset database
python -c "from app.database import engine, Base; Base.metadata.drop_all(engine); Base.metadata.create_all(engine)"

# Check connection
psql postgresql://user:password@localhost:5432/ai_crm_hcp -c "SELECT 1"
```

## 📹 Video Demo (10-15 minutes)

The video demonstration includes:
1. Frontend walkthrough - both Form and Chat interfaces
2. Demo of all 6 LangGraph tools in action
3. Code explanation and architecture overview
4. Summary of project understanding and requirements met

## 📦 Deployment

### Docker (Optional)
Create Dockerfile and docker-compose.yml for production deployment.

### Environment Variables for Production
- Use strong database passwords
- Use production Groq API keys
- Set DEBUG=False
- Configure appropriate CORS_ORIGINS

## 📄 License

This project is licensed under the MIT License - see LICENSE file for details.

## 👥 Contributing

Contributions are welcome! Please create pull requests with clear descriptions of changes.

---

**Project Status**: ✅ Complete
**Last Updated**: 2026-07-14
**Groq LLM**: gemma2-9b-it
**Framework**: LangGraph
# ai-first-crm-hcp-module
