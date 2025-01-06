import { NextRequest } from 'next/server'

export async function POST(request: NextRequest) {
  const data = await request.json()
  
  // Store the generation data as needed
  // This endpoint should match what your Flask endpoint did
  
  return new Response(JSON.stringify({ success: true }), {
    headers: {
      'Content-Type': 'application/json'
    }
  })
} 