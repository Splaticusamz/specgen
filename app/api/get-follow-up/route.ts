import { NextRequest } from 'next/server'
import { Anthropic } from '@anthropic-ai/sdk'
import { GoogleGenerativeAI } from '@google/generative-ai'

export async function POST(request: NextRequest) {
  const data = await request.json()
  const apiKey = data.get('api_key')
  const usingGemini = data.get('using_gemini', false)
  const problem = data.get('problem', '')
  const solution = data.get('solution', '')
  
  if (!apiKey) {
    return new Response(JSON.stringify({ error: 'API Key is empty' }), {
      headers: { 'Content-Type': 'application/json' },
      status: 400
    })
  }

  try {
    let responseText
    if (usingGemini) {
      const genai = new GoogleGenerativeAI(process.env.GOOGLE_API_KEY || '')
      const model = genai.getGenerativeModel({ model: 'gemini-pro' })
      
      const prompt = `You are a technical project analyst. For this project:

Problem: ${problem}
Solution: ${solution}

Your task:
1. Generate exactly 3 highly specific technical questions that are crucial for implementation. These should be focused questions that directly impact development decisions.

2. Recommend the most relevant documentation types from this list based on the project's specific needs:
- cursorrules (Editor configurations)
- prd (Project Requirements Document)
- app_flow (User journeys and workflow)
- tech_stack (Technology choices and dependencies)
- frontend (Frontend architecture)
- schema (Database schema)
- api (API endpoints)
- system_prompts (AI integration)
- deployment (Infrastructure setup)
- security (Security guidelines)
- testing (Testing strategy)

Respond only with a JSON object in this exact format:
{
    "questions": [
        {"id": "q1", "question": "First specific question"},
        {"id": "q2", "question": "Second specific question"},
        {"id": "q3", "question": "Third specific question"}
    ],
    "recommended_docs": ["doc1", "doc2", "doc3"]
}`

      const result = await model.generateContent(prompt)
      responseText = result.response.text()
    } else {
      const anthropic = new Anthropic({
        apiKey: apiKey
      })
      
      const prompt = `You are a helpful AI assistant gathering requirements for a software project. Based on this project idea:

Problem: ${problem}
Solution: ${solution}

First, ask exactly 3 follow-up questions to better understand the project from the user's perspective. These questions should:
- Be easy to understand for non-technical users
- Focus on clarifying the user's needs and expectations
- Help refine the project scope and requirements
- Avoid technical implementation details

Then, based on the project's needs, recommend which documentation types would be most beneficial from this list:
- cursorrules (Editor configurations)
- prd (Project Requirements Document)
- app_flow (User journeys and workflow)
- tech_stack (Technology choices and dependencies)
- frontend (Frontend architecture)
- schema (Database schema)
- api (API endpoints)
- system_prompts (AI integration)
- deployment (Infrastructure setup)
- security (Security guidelines)
- testing (Testing strategy)

Return your response in this JSON format:
{
    "questions": [
        {"id": "q1", "question": "First user-focused question"},
        {"id": "q2", "question": "Second user-focused question"},
        {"id": "q3", "question": "Third user-focused question"}
    ],
    "recommended_docs": ["doc1", "doc2", "doc3"]
}`

      const response = await anthropic.messages.create({
        model: "claude-3-opus-20240229",
        max_tokens: 1000,
        messages: [{ role: "user", content: prompt }]
      })
      responseText = response.content[0].text
    }

    // Parse the response
    try {
      const responseData = JSON.parse(responseText)
      
      // Ensure exactly 3 questions
      if (responseData.questions.length > 3) {
        responseData.questions = responseData.questions.slice(0, 3)
      }
      
      return new Response(JSON.stringify(responseData), {
        headers: { 'Content-Type': 'application/json' }
      })
    } catch (e) {
      // Return a minimal fallback with project-focused questions
      return new Response(JSON.stringify({
        questions: [
          { id: "q1", question: "What are the key technical constraints or requirements for this project?" },
          { id: "q2", question: "What is the expected scale and performance requirements?" },
          { id: "q3", question: "What are the critical integration points in the system?" }
        ],
        recommended_docs: ['prd', 'tech_stack', 'api']
      }), {
        headers: { 'Content-Type': 'application/json' }
      })
    }
  } catch (e) {
    return new Response(JSON.stringify({ error: e.message }), {
      headers: { 'Content-Type': 'application/json' },
      status: 500
    })
  }
} 