import { NextRequest } from 'next/server'

export async function POST(request: NextRequest) {
  const data = await request.json()
  
  // Add your storage logic here that matches your Flask endpoint
  // This endpoint should do whatever your Flask /store-generation-data endpoint did
  
  return new Response(JSON.stringify({ success: true }), {
    headers: {
      'Content-Type': 'application/json'
    }
  })
} 