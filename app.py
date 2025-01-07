import os
import json
import google.generativeai as genai
from anthropic import Anthropic
from flask import Flask, request, jsonify, Response, send_file, send_from_directory, render_template
from zipfile import ZipFile
from io import BytesIO
import time

app = Flask(__name__)

# Initialize Gemini
genai.configure(api_key=os.getenv('GOOGLE_API_KEY', 'your-gemini-api-key'))
gemini_model = genai.GenerativeModel('gemini-pro')

DOCUMENTS = [
    {
        "id": "cursorrules",
        "name": ".cursorrules File",
        "description": "Editor configurations and project settings",
        "optional_prompt": "Any specific editor settings or rules to include?",
        "always_recommended": True
    },
    {
        "id": "prd",
        "name": "Project Requirements Document (PRD)",
        "description": "Detailed project requirements and specifications",
        "optional_prompt": "Any specific sections or focus areas for the PRD?",
        "always_recommended": True
    },
    {
        "id": "app_flow",
        "name": "App Flow Documentation",
        "description": "User journeys and workflow documentation",
        "optional_prompt": "Any specific workflows to highlight?",
        "always_recommended": False
    },
    {
        "id": "tech_stack",
        "name": "Tech Stack & Packages",
        "description": "Technology choices and dependencies",
        "optional_prompt": "Any specific technologies to consider?",
        "always_recommended": True
    },
    {
        "id": "frontend",
        "name": "Frontend Documentation",
        "description": "Frontend architecture and guidelines",
        "optional_prompt": "Any specific UI/UX requirements?",
        "always_recommended": False
    },
    {
        "id": "schema",
        "name": "Schema Design",
        "description": "Database schema and data models",
        "optional_prompt": "Any specific data requirements?",
        "always_recommended": False
    },
    {
        "id": "api",
        "name": "API Documentation",
        "description": "API endpoints and specifications",
        "optional_prompt": "Any specific API requirements?",
        "always_recommended": False
    },
    {
        "id": "system_prompts",
        "name": "System Prompts",
        "description": "AI integration points and templates",
        "optional_prompt": "Any specific AI features to document?",
        "always_recommended": False
    },
    {
        "id": "deployment",
        "name": "Deployment Guide",
        "description": "Infrastructure setup and deployment procedures",
        "optional_prompt": "Any specific deployment requirements or platforms?",
        "always_recommended": False
    },
    {
        "id": "security",
        "name": "Security Guidelines",
        "description": "Security considerations and best practices",
        "optional_prompt": "Any specific security requirements or compliance needs?",
        "always_recommended": False
    },
    {
        "id": "testing",
        "name": "Testing Strategy",
        "description": "Testing approach, test cases, and quality assurance",
        "optional_prompt": "Any specific testing requirements or frameworks?",
        "always_recommended": False
    }
]

def get_llm_client(api_key, using_gemini):
    if using_gemini:
        return gemini_model
    else:
        return Anthropic(api_key=api_key)

def generate_with_gemini(prompt):
    try:
        response = gemini_model.generate_content(prompt)
        
        # If this is a follow-up questions request (contains JSON structure)
        if '"questions":' in prompt:
            try:
                # First try to parse the response directly
                response_text = response.text
                try:
                    json_data = json.loads(response_text)
                except:
                    # If direct parsing fails, try to extract JSON from the response
                    import re
                    json_match = re.search(r'\{[\s\S]*\}', response_text)
                    if json_match:
                        response_text = json_match.group(0)
                        json_data = json.loads(response_text)
                    else:
                        raise Exception("Could not parse JSON response")

                # Ensure the response has both questions and recommended_docs
                if 'questions' not in json_data:
                    json_data['questions'] = []
                if 'recommended_docs' not in json_data:
                    # Add default recommendations based on project type
                    json_data['recommended_docs'] = ['cursorrules', 'prd', 'tech_stack']
                
                return json.dumps(json_data)
            except Exception as e:
                print(f"Error parsing Gemini JSON response: {str(e)}")
                # Return a default structure if parsing fails
                return json.dumps({
                    "questions": [
                        {"id": "q1", "question": "What is your target platform or deployment environment?"},
                        {"id": "q2", "question": "What are your scalability requirements?"},
                        {"id": "q3", "question": "Do you have any specific security requirements?"},
                        {"id": "q4", "question": "What is your preferred technology stack?"},
                        {"id": "q5", "question": "What are your testing requirements?"}
                    ],
                    "recommended_docs": ["cursorrules", "prd", "tech_stack"]
                })
        
        return response.text
    except Exception as e:
        print(f"Gemini error: {str(e)}")
        raise Exception(f"Error with Gemini: {str(e)}")

def generate_with_claude(client, prompt):
    try:
        response = client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except Exception as e:
        print(f"Claude error: {str(e)}")
        raise Exception(f"Error with Claude: {str(e)}")

def get_follow_up_questions_claude(client, problem, solution):
    prompt = f"""You are a helpful AI assistant gathering requirements for a software project. Based on this project idea:

Problem: {problem}
Solution: {solution}

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
{{
    "questions": [
        {{"id": "q1", "question": "First user-focused question"}},
        {{"id": "q2", "question": "Second user-focused question"}},
        {{"id": "q3", "question": "Third user-focused question"}}
    ],
    "recommended_docs": ["doc1", "doc2", "doc3"]
}}"""

    response = client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text

def get_follow_up_questions_gemini(client, problem, solution):
    prompt = f"""You are a technical project analyst. For this project:

Problem: {problem}
Solution: {solution}

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
{{
    "questions": [
        {{"id": "q1", "question": "First specific question"}},
        {{"id": "q2", "question": "Second specific question"}},
        {{"id": "q3", "question": "Third specific question"}}
    ],
    "recommended_docs": ["doc1", "doc2", "doc3"]
}}"""

    response = client.generate_content(prompt)
    return response.text

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/wizard')
def wizard():
    return render_template('index.html', documents=DOCUMENTS)

@app.route('/validate-api-key', methods=['POST'])
def validate_api_key():
    data = request.json
    api_key = data.get('api_key')
    
    if not api_key:
        return jsonify({'valid': False, 'error': 'API Key is empty'})
    
    if api_key == 'USING_GEMINI':
        return jsonify({'valid': True})

    try:
        client = Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1,
            messages=[{"role": "user", "content": "Hi"}]
        )
        return jsonify({'valid': True})
    except Exception as e:
        return jsonify({'valid': False, 'error': str(e)})

@app.route('/get-follow-up', methods=['POST'])
def get_follow_up():
    data = request.json
    api_key = data.get('api_key')
    using_gemini = data.get('using_gemini', False)
    
    if not api_key:
        return jsonify({'error': 'API Key is empty'})

    try:
        client = get_llm_client(api_key, using_gemini)
        
        # Use the appropriate function based on the LLM
        if using_gemini:
            response_text = get_follow_up_questions_gemini(client, data.get('problem', ''), data.get('solution', ''))
        else:
            response_text = get_follow_up_questions_claude(client, data.get('problem', ''), data.get('solution', ''))

        # Parse the response
        try:
            response_data = json.loads(response_text)
            
            # Ensure exactly 3 questions
            if len(response_data.get('questions', [])) > 3:
                response_data['questions'] = response_data['questions'][:3]
            
            return jsonify(response_data)
        except json.JSONDecodeError as e:
            print(f"Error parsing response: {str(e)}")
            print(f"Response text: {response_text}")
            # Return a minimal fallback with project-focused questions
            return jsonify({
                'questions': [
                    {"id": "q1", "question": "What are the key technical constraints or requirements for this project?"},
                    {"id": "q2", "question": "What is the expected scale and performance requirements?"},
                    {"id": "q3", "question": "What are the critical integration points in the system?"}
                ],
                'recommended_docs': ['prd', 'tech_stack', 'api']
            })

    except Exception as e:
        print(f"Error getting follow-up questions: {str(e)}")
        return jsonify({'error': str(e)})

@app.route('/store-generation-data', methods=['POST'])
def store_generation_data():
    try:
        data = request.json
        session_id = str(time.time())  # Use timestamp as session ID
        os.makedirs('sessions', exist_ok=True)
        with open(f'sessions/{session_id}.json', 'w') as f:
            json.dump(data, f)
        return jsonify({'session_id': session_id})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/start-generation', methods=['POST'])
def start_generation():
    try:
        data = request.json
        session_id = str(time.time())
        
        # Store data in session file
        os.makedirs('sessions', exist_ok=True)
        with open(f'sessions/{session_id}.json', 'w') as f:
            json.dump(data, f)
            
        # Start generation in a background thread
        import threading
        thread = threading.Thread(target=generate_docs_in_background, args=(session_id,))
        thread.start()
        
        return jsonify({'session_id': session_id})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/generation-status/<session_id>')
def generation_status(session_id):
    try:
        # Check progress file
        try:
            with open(f'sessions/{session_id}_progress.json', 'r') as f:
                status = json.load(f)
            return jsonify(status)
        except FileNotFoundError:
            return jsonify({'status': 'initializing'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

def generate_docs_in_background(session_id):
    try:
        # Read session data
        with open(f'sessions/{session_id}.json', 'r') as f:
            data = json.load(f)
        
        # Get client
        client = get_llm_client(data['api_key'], data['using_gemini'])
        total_docs = len(data['selected_docs'])
        
        # Generate documents
        for i, doc in enumerate(data['selected_docs'], 1):
            # Update progress
            progress = {
                'status': 'progress',
                'completed': i,
                'total': total_docs,
                'current_file': doc['id']
            }
            with open(f'sessions/{session_id}_progress.json', 'w') as f:
                json.dump(progress, f)
            
            # Generate content
            prompt = f"""Generate content for {doc['id']} documentation.
Project context:
Problem: {data['problem']}
Solution: {data['solution']}
Additional input: {doc.get('optional_input', '')}
Follow-up answers: {json.dumps(data['follow_up_answers'])}
Final notes: {data['final_notes']}

Generate comprehensive and well-structured documentation in markdown format."""

            try:
                if data['using_gemini']:
                    content = generate_with_gemini(prompt)
                else:
                    content = generate_with_claude(client, prompt)
                    
                # Store generated content
                with open(f'sessions/{session_id}_{doc["id"]}.md', 'w') as f:
                    f.write(content)
                    
            except Exception as e:
                error_status = {
                    'status': 'error',
                    'message': f'Error generating {doc["id"]}: {str(e)}'
                }
                with open(f'sessions/{session_id}_progress.json', 'w') as f:
                    json.dump(error_status, f)
                return
        
        # Mark as complete
        complete_status = {
            'status': 'complete',
            'session_id': session_id
        }
        with open(f'sessions/{session_id}_progress.json', 'w') as f:
            json.dump(complete_status, f)
            
    except Exception as e:
        error_status = {
            'status': 'error',
            'message': str(e)
        }
        with open(f'sessions/{session_id}_progress.json', 'w') as f:
            json.dump(error_status, f)

@app.route('/generate', methods=['POST'])
def generate():
    try:
        data = request.json
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({'error': 'No session ID provided'})

        # Read session data
        try:
            with open(f'/tmp/sessions/{session_id}.json', 'r') as f:
                session_data = json.load(f)
        except FileNotFoundError:
            return jsonify({'error': 'Session not found'})

        # Create ZIP file with generated documents
        memory_file = BytesIO()
        with ZipFile(memory_file, 'w') as zf:
            for doc in session_data['selected_docs']:
                doc_id = doc['id']
                try:
                    with open(f'/tmp/sessions/{session_id}_{doc_id}.md', 'r') as f:
                        content = f.read()
                        zf.writestr(f"{doc_id}.md", content)
                except FileNotFoundError:
                    print(f"Warning: Content file not found for {doc_id}")
                    continue

        # Clean up session files
        try:
            os.remove(f'/tmp/sessions/{session_id}.json')
            for doc in session_data['selected_docs']:
                try:
                    os.remove(f'/tmp/sessions/{session_id}_{doc["id"]}.md')
                except FileNotFoundError:
                    continue
        except Exception as e:
            print(f"Warning: Error cleaning up session files: {str(e)}")

        memory_file.seek(0)
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name='project_docs.zip'
        )

    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/generate-progress/stream')
def generate_progress_stream():
    try:
        # Get query parameters
        problem = request.args.get('problem', '')
        solution = request.args.get('solution', '')
        follow_up_answers = json.loads(request.args.get('follow_up_answers', '{}'))
        selected_docs = json.loads(request.args.get('selected_docs', '[]'))
        final_notes = request.args.get('final_notes', '')
        api_key = request.args.get('api_key', '')
        using_gemini = request.args.get('using_gemini', 'false').lower() == 'true'

        # Create session in /tmp
        session_id = str(time.time())
        os.makedirs('/tmp/sessions', exist_ok=True)

        # Store initial session data
        data = {
            'problem': problem,
            'solution': solution,
            'follow_up_answers': follow_up_answers,
            'selected_docs': selected_docs,
            'final_notes': final_notes,
            'api_key': api_key,
            'using_gemini': using_gemini,
            'completed_docs': [],
            'status': 'in_progress'
        }
        with open(f'/tmp/sessions/{session_id}.json', 'w') as f:
            json.dump(data, f)

        # Start background thread for generation
        def generate_docs():
            try:
                client = get_llm_client(api_key, using_gemini)
                for doc in selected_docs:
                    prompt = f"""Generate content for {doc['id']} documentation.
Project context:
Problem: {problem}
Solution: {solution}
Additional input: {doc.get('optional_input', '')}
Follow-up answers: {json.dumps(follow_up_answers)}
Final notes: {final_notes}

Generate comprehensive and well-structured documentation in markdown format."""

                    try:
                        if using_gemini:
                            content = generate_with_gemini(prompt)
                        else:
                            content = generate_with_claude(client, prompt)

                        with open(f'/tmp/sessions/{session_id}_{doc["id"]}.md', 'w') as f:
                            f.write(content)

                        # Update progress
                        with open(f'/tmp/sessions/{session_id}.json', 'r') as f:
                            data = json.load(f)
                        data['completed_docs'].append(doc['id'])
                        with open(f'/tmp/sessions/{session_id}.json', 'w') as f:
                            json.dump(data, f)
                    except Exception as e:
                        print(f"Error generating {doc['id']}: {str(e)}")
                        continue

                # Mark as complete
                with open(f'/tmp/sessions/{session_id}.json', 'r') as f:
                    data = json.load(f)
                data['status'] = 'complete'
                with open(f'/tmp/sessions/{session_id}.json', 'w') as f:
                    json.dump(data, f)

            except Exception as e:
                print(f"Error in generate_docs: {str(e)}")
                with open(f'/tmp/sessions/{session_id}.json', 'r') as f:
                    data = json.load(f)
                data['status'] = 'error'
                data['error'] = str(e)
                with open(f'/tmp/sessions/{session_id}.json', 'w') as f:
                    json.dump(data, f)

        import threading
        thread = threading.Thread(target=generate_docs)
        thread.start()

        # Return session ID immediately
        return jsonify({
            'status': 'started',
            'session_id': session_id,
            'total': len(selected_docs)
        })

    except Exception as e:
        print(f"Error in generate_progress_stream: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/check-progress/<session_id>')
def check_progress(session_id):
    try:
        with open(f'/tmp/sessions/{session_id}.json', 'r') as f:
            data = json.load(f)
        
        return jsonify({
            'status': data.get('status', 'unknown'),
            'completed': len(data.get('completed_docs', [])),
            'total': len(data.get('selected_docs', [])),
            'error': data.get('error')
        })

    except FileNotFoundError:
        return jsonify({'error': 'Session not found'}), 404
    except Exception as e:
        print(f"Error in check_progress: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000) 