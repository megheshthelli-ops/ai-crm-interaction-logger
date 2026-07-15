# AI-First CRM HCP Module

An AI-powered Customer Relationship Management (CRM) application for managing Healthcare Professional (HCP) interactions. The application enables users to log, edit, search, summarize, and manage HCP interactions using natural language through an AI Assistant powered by **LangGraph** and **Groq LLM**.

---

# Project Overview

This project is built as an AI-first CRM system where users interact with an AI assistant instead of manually filling forms.

The AI Assistant extracts information from natural language, automatically fills the interaction form, stores the interaction in the database, and allows users to retrieve or update interaction details through conversational prompts.

---

# Features

- AI-assisted interaction logging
- AI-assisted interaction editing
- Search previous HCP interactions
- Summarize interactions
- AI-generated follow-up suggestions
- PostgreSQL database integration
- LangGraph tool-based architecture
- Responsive React frontend
- FastAPI backend

---

# Tech Stack

## Frontend

- React.js
- Material UI
- Axios

## Backend

- Python
- FastAPI
- SQLAlchemy
- LangGraph

## Database

- PostgreSQL

## AI

- Groq API
- Llama 3.3 70B Versatile

---

# Project Structure

```
ai-first-crm-hcp-module/
│
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── ...
│
├── backend/
│   ├── app/
│   ├── requirements.txt
│   ├── alembic/
│   ├── .env
│   └── ...
│
├── screenshots/
│
└── README.md
```

---

# Installation

## Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/ai-first-crm-hcp-module.git

cd ai-first-crm-hcp-module
```

---

# Environment Variables

Create a `.env` file inside the backend folder.

```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/hcp_crm

GROQ_API_KEY=your_groq_api_key

MODEL_NAME=llama-3.3-70b-versatile
```

---

# Database Setup

Create a PostgreSQL database.

Example:

```
Database Name:
hcp_crm
```

Run migrations (if applicable):

```bash
alembic upgrade head
```

Or create the tables using the provided backend setup.

---

# Backend Setup

Navigate to backend

```bash
cd backend
```

Create virtual environment

### Windows

```bash
python -m venv venv
```

Activate virtual environment

```bash
venv\Scripts\activate
```

Install dependencies

```bash
pip install -r requirements.txt
```

Run backend

```bash
python -m uvicorn app.main:app --reload
```

Backend runs at

```
http://localhost:8000
```

---

# Frontend Setup

Navigate to frontend

```bash
cd frontend
```

Install dependencies

```bash
npm install
```

Run frontend

```bash
npm run dev
```

Frontend runs at

```
http://localhost:5173
```

---

# LangGraph Flow

```
User Prompt
      │
      ▼
 AI Assistant
      │
      ▼
 LangGraph Agent
      │
      ▼
 Select Appropriate Tool
      │
      ▼
 Execute Tool
      │
      ▼
 Database Update / Retrieval
      │
      ▼
 AI Response
      │
      ▼
 React UI Updates Automatically
```

---

# AI Tools

## 1. Log Interaction

Extracts structured information from natural language and automatically fills the interaction form.

Example:

```
Today I met Dr. John Smith.

We discussed CardioPlus.

The sentiment was positive.
```

---

## 2. Edit Interaction

Updates only the specified fields without affecting the remaining interaction details.

Example:

```
Change the sentiment to Neutral.

Remove brochures.

Change the doctor's name to Dr. Michael Brown.
```

---

## 3. Search Interaction

Retrieves interaction history for a specific HCP or based on user queries.

Example:

```
Show my interaction with Dr. Michael Brown.
```

---

## 4. Summarize Interaction

Generates concise summaries of recorded interactions.

Example:

```
Summarize today's interaction.
```

---

## 5. Follow-up Recommendation

Provides AI-generated follow-up recommendations based on previous interactions.

Example:

```
What should I do next?
```

---

# Future Improvements

- Voice-to-text interaction logging
- Multi-user authentication
- Email integration
- Calendar integration
- Advanced analytics dashboard
- PDF report generation

---

# Author

**Thelli Meghesh**

---

# License

This project was developed as part of a technical assessment for demonstration purposes.
