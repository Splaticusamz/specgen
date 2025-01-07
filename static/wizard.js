async function generateDocs() {
    try {
        const problem = document.getElementById('problem').value;
        const solution = document.getElementById('solution').value;
        const followUpAnswers = Alpine.store('followUpAnswers');
        const selectedDocs = Alpine.store('selectedDocs');
        const finalNotes = document.getElementById('final-notes').value;
        const apiKey = document.getElementById('api-key').value;
        const usingGemini = document.getElementById('using-gemini').checked;

        // Start generation
        const response = await fetch(`/generate-progress/stream?problem=${encodeURIComponent(problem)}&solution=${encodeURIComponent(solution)}&follow_up_answers=${encodeURIComponent(JSON.stringify(followUpAnswers))}&selected_docs=${encodeURIComponent(JSON.stringify(selectedDocs))}&final_notes=${encodeURIComponent(finalNotes)}&api_key=${encodeURIComponent(apiKey)}&using_gemini=${usingGemini}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        if (data.error) {
            throw new Error(data.error);
        }

        const sessionId = data.session_id;
        const total = data.total;
        let completed = 0;

        // Update progress bar
        const progressBar = document.getElementById('progress-bar');
        progressBar.style.width = '0%';
        document.getElementById('generation-progress').classList.remove('hidden');

        // Poll for progress
        while (true) {
            const progressResponse = await fetch(`/check-progress/${sessionId}`);
            if (!progressResponse.ok) {
                throw new Error(`HTTP error! status: ${progressResponse.status}`);
            }

            const progressData = await progressResponse.json();
            if (progressData.error) {
                throw new Error(progressData.error);
            }

            completed = progressData.completed;
            const percentage = (completed / total) * 100;
            progressBar.style.width = `${percentage}%`;

            if (progressData.status === 'complete') {
                // Generation complete, download the ZIP
                const response = await fetch('/generate', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ session_id: sessionId })
                });

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                // Trigger download
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'project_docs.zip';
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                
                document.getElementById('generation-progress').classList.add('hidden');
                break;
            } else if (progressData.status === 'error') {
                throw new Error(progressData.error || 'An error occurred during generation');
            }

            // Wait before polling again
            await new Promise(resolve => setTimeout(resolve, 1000));
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error generating documentation: ' + error.message);
        document.getElementById('generation-progress').classList.add('hidden');
    }
} 