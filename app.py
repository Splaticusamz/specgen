import os
import json
import google.generativeai as genai
from anthropic import Anthropic
import requests
from flask import Flask, request, jsonify, Response, send_file, send_from_directory, render_template
from flask_cors import CORS
from zipfile import ZipFile
from io import BytesIO
import time
from collections import defaultdict

app = Flask(__name__)
CORS(app, resources={
    r"/generate-progress/stream": {
        "origins": "*",
        "methods": ["GET", "OPTIONS"],
        "allow_headers": ["Content-Type"],
        "expose_headers": ["Content-Type"],
        "supports_credentials": False
    }
})

# In-memory storage for session data
session_storage = defaultdict(dict)

# Initialize Gemini
genai.configure(api_key=os.getenv('GOOGLE_API_KEY', 'your-gemini-api-key'))
gemini_model = genai.GenerativeModel('gemini-pro')

# Deepseek configuration
DEEPSEEK_API_KEY = "sk-6f12bef7309943e6b726153ce7e1e645"
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

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

def generate_with_deepseek(prompt):
    try:
        print(f"Sending request to Deepseek with prompt: {prompt[:100]}...")
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 2000
        }
        print("Making request to Deepseek API...")
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data)
        print(f"Deepseek response status: {response.status_code}")
        response.raise_for_status()
        response_text = response.json()['choices'][0]['message']['content']
        print(f"Deepseek response: {response_text[:100]}...")

        # If this is a follow-up questions request (contains JSON structure)
        if '"questions":' in prompt:
            try:
                # First try to parse the response directly
                try:
                    json_data = json.loads(response_text)
                    print("Successfully parsed JSON response")
                except json.JSONDecodeError as e:
                    print(f"Failed to parse JSON directly: {str(e)}")
                    # If direct parsing fails, try to extract JSON from the response
                    import re
                    json_match = re.search(r'\{[\s\S]*\}', response_text)
                    if json_match:
                        response_text = json_match.group(0)
                        print(f"Extracted JSON: {response_text[:100]}...")
                        json_data = json.loads(response_text)
                    else:
                        raise Exception("Could not parse JSON response")

                # Ensure the response has both questions and recommended_docs
                if 'questions' not in json_data:
                    print("No questions in response, adding default questions")
                    json_data['questions'] = [
                        {"id": "q1", "question": "What are the key technical constraints or requirements for this project?"},
                        {"id": "q2", "question": "What is the expected scale and performance requirements?"},
                        {"id": "q3", "question": "What are the critical integration points in the system?"}
                    ]
                if 'recommended_docs' not in json_data:
                    print("No recommended_docs in response, adding defaults")
                    json_data['recommended_docs'] = ['cursorrules', 'prd', 'tech_stack']
                
                return json.dumps(json_data)
            except Exception as e:
                print(f"Error parsing Deepseek JSON response: {str(e)}")
                print(f"Full response text: {response_text}")
                # Return a default structure if parsing fails
                return json.dumps({
                    "questions": [
                        {"id": "q1", "question": "What are the key technical constraints or requirements for this project?"},
                        {"id": "q2", "question": "What is the expected scale and performance requirements?"},
                        {"id": "q3", "question": "What are the critical integration points in the system?"}
                    ],
                    "recommended_docs": ["cursorrules", "prd", "tech_stack"]
                })
        
        return response_text
    except Exception as e:
        print(f"Deepseek error: {str(e)}")
        raise Exception(f"Error with Deepseek: {str(e)}")

def get_llm_client(api_key, using_gemini, using_deepseek=False):
    if using_gemini:
        return gemini_model
    elif using_deepseek:
        return None  # Deepseek doesn't need a client
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
                print(f"Gemini raw response: {response_text[:100]}...")
                try:
                    json_data = json.loads(response_text)
                    print("Successfully parsed JSON response")
                except json.JSONDecodeError as e:
                    print(f"Failed to parse JSON directly: {str(e)}")
                    # If direct parsing fails, try to extract JSON from the response
                    import re
                    json_match = re.search(r'\{[\s\S]*\}', response_text)
                    if json_match:
                        response_text = json_match.group(0)
                        print(f"Extracted JSON: {response_text[:100]}...")
                        json_data = json.loads(response_text)
                    else:
                        raise Exception("Could not parse JSON response")

                # Ensure the response has both questions and recommended_docs
                if 'questions' not in json_data:
                    print("No questions in response, adding default questions")
                    json_data['questions'] = [
                        {"id": "q1", "question": "What are the key technical constraints or requirements for this project?"},
                        {"id": "q2", "question": "What is the expected scale and performance requirements?"},
                        {"id": "q3", "question": "What are the critical integration points in the system?"}
                    ]
                elif len(json_data['questions']) < 3:
                    print("Adding default questions to reach 3")
                    default_questions = [
                        {"id": "q1", "question": "What are the key technical constraints or requirements for this project?"},
                        {"id": "q2", "question": "What is the expected scale and performance requirements?"},
                        {"id": "q3", "question": "What are the critical integration points in the system?"}
                    ]
                    json_data['questions'].extend(default_questions[len(json_data['questions']):])
                elif len(json_data['questions']) > 3:
                    print("Trimming questions to exactly 3")
                    json_data['questions'] = json_data['questions'][:3]
                
                if 'recommended_docs' not in json_data or not json_data['recommended_docs']:
                    print("No recommended_docs in response, adding defaults")
                    json_data['recommended_docs'] = ['cursorrules', 'prd', 'tech_stack']
                
                return json.dumps(json_data)
            except Exception as e:
                print(f"Error parsing Gemini JSON response: {str(e)}")
                print(f"Full response text: {response_text}")
                # Return a default structure if parsing fails
                return json.dumps({
                    "questions": [
                        {"id": "q1", "question": "What are the key technical constraints or requirements for this project?"},
                        {"id": "q2", "question": "What is the expected scale and performance requirements?"},
                        {"id": "q3", "question": "What are the critical integration points in the system?"}
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

You must respond with a valid JSON object in this exact format, with no additional text before or after:
{{
    "questions": [
        {{"id": "q1", "question": "First specific question"}},
        {{"id": "q2", "question": "Second specific question"}},
        {{"id": "q3", "question": "Third specific question"}}
    ],
    "recommended_docs": ["doc1", "doc2", "doc3"]
}}"""

    print(f"Sending prompt to Gemini: {prompt[:100]}...")
    response = client.generate_content(prompt)
    print(f"Got response from Gemini: {response.text[:100]}...")
    return response.text

def get_follow_up_questions_deepseek(problem, solution):
    print("Starting Deepseek follow-up questions generation...")
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

    try:
        print(f"Sending request to Deepseek with prompt: {prompt[:100]}...")
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 2000
        }
        print("Making request to Deepseek API...")
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data)
        print(f"Deepseek response status: {response.status_code}")
        response.raise_for_status()
        response_text = response.json()['choices'][0]['message']['content']
        print(f"Deepseek response: {response_text[:100]}...")

        try:
            # First try to parse the response directly
            json_data = json.loads(response_text)
            print("Successfully parsed JSON response")
            
            # Ensure the response has both questions and recommended_docs
            if 'questions' not in json_data:
                print("No questions in response, adding default questions")
                json_data['questions'] = [
                    {"id": "q1", "question": "What are the key technical constraints or requirements for this project?"},
                    {"id": "q2", "question": "What is the expected scale and performance requirements?"},
                    {"id": "q3", "question": "What are the critical integration points in the system?"}
                ]
            elif len(json_data['questions']) < 3:
                print("Adding default questions to reach 3")
                default_questions = [
                    {"id": "q1", "question": "What are the key technical constraints or requirements for this project?"},
                    {"id": "q2", "question": "What is the expected scale and performance requirements?"},
                    {"id": "q3", "question": "What are the critical integration points in the system?"}
                ]
                json_data['questions'].extend(default_questions[len(json_data['questions']):])
            elif len(json_data['questions']) > 3:
                print("Trimming questions to exactly 3")
                json_data['questions'] = json_data['questions'][:3]
            
            if 'recommended_docs' not in json_data or not json_data['recommended_docs']:
                print("No recommended_docs in response, adding defaults")
                json_data['recommended_docs'] = ['cursorrules', 'prd', 'tech_stack']
            
            return json.dumps(json_data)
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON directly: {str(e)}")
            # If direct parsing fails, try to extract JSON from the response
            import re
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                response_text = json_match.group(0)
                print(f"Extracted JSON: {response_text[:100]}...")
                try:
                    json_data = json.loads(response_text)
                    if 'questions' not in json_data:
                        json_data['questions'] = [
                            {"id": "q1", "question": "What are the key technical constraints or requirements for this project?"},
                            {"id": "q2", "question": "What is the expected scale and performance requirements?"},
                            {"id": "q3", "question": "What are the critical integration points in the system?"}
                        ]
                    elif len(json_data['questions']) < 3:
                        default_questions = [
                            {"id": "q1", "question": "What are the key technical constraints or requirements for this project?"},
                            {"id": "q2", "question": "What is the expected scale and performance requirements?"},
                            {"id": "q3", "question": "What are the critical integration points in the system?"}
                        ]
                        json_data['questions'].extend(default_questions[len(json_data['questions']):])
                    elif len(json_data['questions']) > 3:
                        json_data['questions'] = json_data['questions'][:3]
                    
                    if 'recommended_docs' not in json_data or not json_data['recommended_docs']:
                        json_data['recommended_docs'] = ['cursorrules', 'prd', 'tech_stack']
                    return json.dumps(json_data)
                except:
                    print("Failed to parse extracted JSON")
            
            print("Returning default response")
            return json.dumps({
                "questions": [
                    {"id": "q1", "question": "What are the key technical constraints or requirements for this project?"},
                    {"id": "q2", "question": "What is the expected scale and performance requirements?"},
                    {"id": "q3", "question": "What are the critical integration points in the system?"}
                ],
                "recommended_docs": ["cursorrules", "prd", "tech_stack"]
            })
    except Exception as e:
        print(f"Deepseek error: {str(e)}")
        raise Exception(f"Error with Deepseek: {str(e)}")

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
    print("Received get-follow-up request")
    data = request.json
    api_key = data.get('api_key')
    using_gemini = data.get('using_gemini', False)
    using_deepseek = data.get('using_deepseek', False)
    
    print(f"Request params: using_gemini={using_gemini}, using_deepseek={using_deepseek}")
    
    if not api_key and not using_gemini and not using_deepseek:
        print("No API key or model selection provided")
        return jsonify({'error': 'API Key is empty'})

    try:
        # Use the appropriate function based on the LLM
        if using_gemini:
            print("Using Gemini for follow-up questions")
            client = get_llm_client(api_key, using_gemini)
            response_text = get_follow_up_questions_gemini(client, data.get('problem', ''), data.get('solution', ''))
        elif using_deepseek:
            print("Using Deepseek for follow-up questions")
            response_text = get_follow_up_questions_deepseek(data.get('problem', ''), data.get('solution', ''))
        else:
            print("Using Claude for follow-up questions")
            client = get_llm_client(api_key, using_gemini)
            response_text = get_follow_up_questions_claude(client, data.get('problem', ''), data.get('solution', ''))

        print(f"Got response text: {response_text[:100]}...")

        # Parse the response
        try:
            response_data = json.loads(response_text)
            print("Successfully parsed response JSON")
            
            # Ensure exactly 3 questions
            if len(response_data.get('questions', [])) > 3:
                print("Trimming questions to exactly 3")
                response_data['questions'] = response_data['questions'][:3]
            elif len(response_data.get('questions', [])) < 3:
                print("Adding default questions to reach 3")
                default_questions = [
                    {"id": "q1", "question": "What are the key technical constraints or requirements for this project?"},
                    {"id": "q2", "question": "What is the expected scale and performance requirements?"},
                    {"id": "q3", "question": "What are the critical integration points in the system?"}
                ]
                response_data['questions'].extend(default_questions[len(response_data['questions']):])
            
            # Ensure recommended_docs exists and is not empty
            if 'recommended_docs' not in response_data or not response_data['recommended_docs']:
                print("Adding default recommended_docs")
                response_data['recommended_docs'] = ['cursorrules', 'prd', 'tech_stack']
            
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
                'recommended_docs': ['cursorrules', 'prd', 'tech_stack']
            })

    except Exception as e:
        print(f"Error getting follow-up questions: {str(e)}")
        print(f"Full error details: {e.__class__.__name__}: {str(e)}")
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
        problem = data.get('problem', '')
        solution = data.get('solution', '')
        follow_up_answers = data.get('follow_up_answers', {})
        selected_docs = data.get('selected_docs', [])
        final_notes = data.get('final_notes', '')
        api_key = data.get('api_key', '')
        using_gemini = data.get('using_gemini', False)
        using_deepseek = data.get('using_deepseek', False)

        session_id = str(time.time())
        session_storage[session_id] = {
            'problem': problem,
            'solution': solution,
            'follow_up_answers': follow_up_answers,
            'selected_docs': selected_docs,
            'final_notes': final_notes,
            'api_key': api_key,
            'using_gemini': using_gemini,
            'using_deepseek': using_deepseek,
            'completed_docs': [],
            'generated_content': {},
            'status': 'in_progress',
            'total': len(selected_docs),
            'completed': 0,
            'current_file': ''
        }

        def generate_docs():
            try:
                client = get_llm_client(api_key, using_gemini, using_deepseek)
                
                for doc in selected_docs:
                    session_storage[session_id]['current_file'] = doc['id']
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
                        elif using_deepseek:
                            content = generate_with_deepseek(prompt)
                        else:
                            content = generate_with_claude(client, prompt)

                        session_storage[session_id]['generated_content'][doc['id']] = content
                        session_storage[session_id]['completed_docs'].append(doc['id'])
                        session_storage[session_id]['completed'] += 1

                    except Exception as e:
                        print(f"Error generating {doc['id']}: {str(e)}")
                        session_storage[session_id]['status'] = 'error'
                        session_storage[session_id]['error'] = str(e)
                        return

                session_storage[session_id]['status'] = 'complete'

            except Exception as e:
                print(f"Error in generate_docs: {str(e)}")
                session_storage[session_id]['status'] = 'error'
                session_storage[session_id]['error'] = str(e)

        # Start generation in background
        import threading
        thread = threading.Thread(target=generate_docs)
        thread.start()

        return jsonify({
            'status': 'started',
            'session_id': session_id,
            'total': len(selected_docs)
        })

    except Exception as e:
        print(f"Error in start_generation: {str(e)}")
        return jsonify({'error': str(e)})

@app.route('/check-progress/<session_id>')
def check_progress(session_id):
    try:
        if session_id not in session_storage:
            return jsonify({'error': 'Session not found'}), 404
            
        data = session_storage[session_id]
        return jsonify({
            'status': data.get('status', 'unknown'),
            'completed': data.get('completed', 0),
            'total': data.get('total', 0),
            'current_file': data.get('current_file', ''),
            'error': data.get('error')
        })

    except Exception as e:
        print(f"Error in check_progress: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/generate', methods=['POST'])
def generate():
    try:
        data = request.json
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({'error': 'No session ID provided'})

        if session_id not in session_storage:
            return jsonify({'error': 'Session not found'})

        session_data = session_storage[session_id]
        
        # Create ZIP file with generated documents
        memory_file = BytesIO()
        with ZipFile(memory_file, 'w') as zf:
            for doc in session_data['selected_docs']:
                doc_id = doc['id']
                if doc_id in session_data['generated_content']:
                    content = session_data['generated_content'][doc_id]
                    zf.writestr(f"{doc_id}.md", content)

        # Clean up session data
        del session_storage[session_id]

        # Prepare the response
        memory_file.seek(0)
        response = send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name='project_docs.zip'
        )
        response.headers['Content-Type'] = 'application/zip'
        return response

    except Exception as e:
        print(f"Error in generate: {str(e)}")
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True, port=5000) 