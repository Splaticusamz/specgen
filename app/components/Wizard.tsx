'use client';
import { useState, useEffect } from 'react';

export default function Wizard() {
  const [problem, setProblem] = useState('');
  const [solution, setSolution] = useState('');
  const [followUpAnswers, setFollowUpAnswers] = useState({});
  const [finalNotes, setFinalNotes] = useState('');
  const [usingGemini, setUsingGemini] = useState(false);
  
  const handleGenerate = async () => {
    const selectedDocs = []; // Add your docs logic here
    
    const queryParams = new URLSearchParams({
      problem: problem,
      solution: solution,
      follow_up_answers: JSON.stringify(followUpAnswers),
      selected_docs: JSON.stringify(selectedDocs),
      final_notes: finalNotes,
      api_key: 'USING_GEMINI', // Get this from env or state
      using_gemini: String(usingGemini)
    });

    const eventSource = new EventSource(`/api/generate-progress/stream?${queryParams}`);
    
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      // Handle progress updates
    };

    eventSource.onerror = (error) => {
      console.error('EventSource failed:', error);
      eventSource.close();
    };
  };

  return (
    // Your wizard UI here
  );
} 