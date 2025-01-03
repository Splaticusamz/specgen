# SpecGen - AI-Powered Project Documentation Generator

SpecGen is a web-based wizard that helps you generate comprehensive project documentation using AI. Available at [specgen.dev](https://specgen.dev), it guides you through a series of questions about your project and generates a complete set of documentation files.

## Features

- **Multiple AI Options**: 
  - Use Google's Gemini (Free)
  - Use Anthropic's Claude (Premium quality with API key)
- **Generated Documentation**:
  - Project Requirements Document (PRD)
  - App Flow Documentation
  - Tech Stack & Packages Documentation
  - Frontend Code Documentation
  - Schema Design Documentation
  - API Documentation
  - System Prompts
  - `.cursorrules` file

## Local Development Setup

1. Clone this repository:
```bash
git clone <repository-url>
cd specgen
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the project root:
```
# Required for session management
FLASK_SECRET_KEY=your_secret_key_here

# For Gemini free tier
GOOGLE_API_KEY=your_gemini_api_key
```

## Usage

1. Start the Flask development server:
```bash
python app.py
```

2. Open your browser and navigate to `http://localhost:5000`

3. Choose your preferred AI model:
   - Gemini (Free tier)
   - Claude (Requires API key)

4. Follow the wizard's steps:
   - Describe your project's problem and solution
   - Answer follow-up questions
   - Select required documentation
   - Add any final notes

5. Download the generated ZIP file containing all documentation

## Requirements

- Python 3.8+
- Modern web browser
- For Claude: Anthropic API key
- For Gemini: Google AI API key

## Support

For support or custom development inquiries, contact: support@specgen.dev

## License

This project is open source and licensed under the MIT License.

---
Created by [Splaticus](https://github.com/splaticus) 