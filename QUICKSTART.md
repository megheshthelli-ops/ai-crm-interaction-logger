# 🚀 Quick Start Guide

## 5-Minute Setup

### Step 1: Backend Setup (Terminal 1)
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/Scripts/activate  # Windows
# or: source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Create .env file with your Groq API key
# Edit backend/.env and set GROQ_API_KEY

# Initialize database (PostgreSQL required)
python -c "from app.database import init_db; init_db()"

# (Optional) Load sample data
python init_sample_data.py

# Run server
uvicorn app.main:app --reload --port 8000
```

✅ Backend ready at: http://localhost:8000
📚 API Docs at: http://localhost:8000/docs

### Step 2: Frontend Setup (Terminal 2)
```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

✅ Frontend ready at: http://localhost:5173

---

## 🎯 Using the Application

### Interface 1: Structured Form
1. Click "📋 Log Interaction (Form)" tab
2. Select HCP from dropdown
3. Fill in interaction details
4. Click "Log Interaction"
5. AI automatically summarizes!

### Interface 2: AI Chat
1. Click "💬 AI Chat Assistant" tab
2. Type naturally: "Met with Dr. Smith about cardiac treatments..."
3. Chat continues to extract details
4. Interaction automatically logged

### Interface 3: History
1. Click "📊 Interaction History" tab
2. View all past interactions
3. Edit or delete as needed
4. See AI-generated summaries

---

## 📋 The 6 LangGraph Tools in Action

### Tool 1: log_interaction
**What**: Capture & summarize interactions
**When**: User submits form or chat
**How**: LLM analyzes and auto-summarizes

### Tool 2: edit_interaction  
**What**: Modify recorded interactions
**When**: User clicks Edit button
**How**: Updates database, regenerates summary if content changes

### Tool 3: search_hcp
**What**: Find Healthcare Professionals
**When**: User searches in sidebar or form
**How**: Searches by name, specialty, organization

### Tool 4: get_interaction_history
**What**: Retrieve past interactions
**When**: User views history tab
**How**: Fetches from database, ordered by date

### Tool 5: suggest_follow_up_actions
**When**: AI suggests next steps
**What**: Uses LLM to analyze interaction
**How**: Click "Get Follow-up" button on interaction

### Tool 6: get_recommended_materials
**What**: Suggest relevant materials/samples
**When**: Based on discussion topics
**How**: Searches materials database

---

## 🔑 Key Environment Variables

Set these in `backend/.env`:

```env
# REQUIRED - Get from https://console.groq.com
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxx
GROQ_MODEL=gemma2-9b-it

# Database (use PostgreSQL for best results)
DATABASE_URL=postgresql://postgres:password@localhost:5432/ai_crm_hcp

# Frontend communication
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Debug mode (set to False in production)
DEBUG=True
```

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` |
| Database connection error | Check DATABASE_URL in .env, ensure PostgreSQL is running |
| Frontend can't reach API | Verify backend running on :8000, check CORS_ORIGINS |
| Groq API error | Get API key from https://console.groq.com, check GROQ_API_KEY |
| "AI not generating summaries" | Verify GROQ_API_KEY is set correctly |

---

## 📊 Architecture Overview

```
┌─────────────────────────┐
│   React Frontend        │
│  (Vite + Redux + MUI)   │
└────────────┬────────────┘
             │ HTTP/JSON
             ↓
┌─────────────────────────┐
│    FastAPI Backend      │
│  (SQLAlchemy + Async)   │
└────────────┬────────────┘
             │
     ┌───────┴───────┬─────────────┐
     ↓               ↓             ↓
  Database      LangGraph       Groq LLM
  (PostgreSQL)   (6 Tools)    (AI Engine)
```

---

## 🎓 Learning Resources

- **FastAPI**: https://fastapi.tiangolo.com
- **React**: https://react.dev
- **Redux**: https://redux.js.org
- **LangGraph**: https://langchain.com/langgraph
- **Groq**: https://console.groq.com/docs/models

---

## 📹 What to Include in Your Video

1. **Form Demo** (2-3 min)
   - Show selecting HCP
   - Fill form fields
   - Submit and see AI summary
   
2. **Chat Demo** (2-3 min)
   - Natural language conversation
   - Auto-extraction of details
   - Interaction logged

3. **Tools Demo** (3-4 min)
   - Show search_hcp results
   - View interaction_history
   - Get suggest_follow_up_actions
   - Show get_recommended_materials
   - Demonstrate edit_interaction
   - Explain log_interaction with LLM

4. **Code Walkthrough** (2-3 min)
   - Show LangGraph tools architecture
   - Groq LLM integration
   - Redux state management
   - API endpoints

5. **Summary** (1-2 min)
   - Explain how it meets requirements
   - Highlight LangGraph usage
   - Mention LLM capabilities

---

## ✅ Verification Checklist

- [ ] Backend running on :8000
- [ ] Frontend running on :5173
- [ ] API docs accessible (/docs)
- [ ] Can log interaction with form
- [ ] Can chat with AI assistant
- [ ] Can view interaction history
- [ ] LLM summaries working
- [ ] Search HCP working
- [ ] Follow-up suggestions working
- [ ] Material recommendations working

---

**Happy coding! 🎉**
