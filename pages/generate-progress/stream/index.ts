import type { NextApiRequest, NextApiResponse } from 'next'

export default function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'GET') {
    return res.status(405).end()
  }

  res.setHeader('Content-Type', 'text/event-stream')
  res.setHeader('Cache-Control', 'no-cache')
  res.setHeader('Connection', 'keep-alive')

  const selectedDocs = JSON.parse(req.query.selected_docs as string || '[]')

  const sendUpdate = (index: number, doc: any) => {
    res.write(`data: ${JSON.stringify({
      status: 'progress',
      completed: index,
      total: selectedDocs.length,
      current_file: doc.id
    })}\n\n`)
  }

  selectedDocs.forEach((doc: any, index: number) => {
    setTimeout(() => {
      sendUpdate(index, doc)
      if (index === selectedDocs.length - 1) {
        res.write(`data: ${JSON.stringify({ status: 'complete' })}\n\n`)
        res.end()
      }
    }, index * 1000)
  })
} 