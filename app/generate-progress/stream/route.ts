import { NextRequest } from 'next/server'

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams
  const problem = searchParams.get('problem')
  const solution = searchParams.get('solution')
  const followUpAnswers = JSON.parse(searchParams.get('follow_up_answers') || '{}')
  const selectedDocs = JSON.parse(searchParams.get('selected_docs') || '[]')
  const finalNotes = searchParams.get('final_notes')
  const apiKey = searchParams.get('api_key')
  const usingGemini = searchParams.get('using_gemini') === 'true'

  // Set up Server-Sent Events
  const encoder = new TextEncoder()
  const stream = new ReadableStream({
    async start(controller) {
      try {
        // Replicate your Flask SSE logic here
        for (const doc of selectedDocs) {
          controller.enqueue(encoder.encode(`data: ${JSON.stringify({
            status: 'progress',
            completed: selectedDocs.indexOf(doc),
            total: selectedDocs.length,
            current_file: doc.id
          })}\n\n`))
          
          // Add your generation logic here
          await new Promise(resolve => setTimeout(resolve, 1000)) // Simulate work
        }
        
        controller.enqueue(encoder.encode(`data: ${JSON.stringify({
          status: 'complete'
        })}\n\n`))
        
        controller.close()
      } catch (error) {
        controller.error(error)
      }
    }
  })

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
    },
  })
} 