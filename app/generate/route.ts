import { NextRequest } from 'next/server'

export async function POST(request: NextRequest) {
  const data = await request.json()
  
  // Add your generation logic here
  
  return new Response(JSON.stringify({ success: true }), {
    headers: {
      'Content-Type': 'application/json'
    }
  })
} 