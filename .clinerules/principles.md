# Cline Project Principles

## Tech Stack
- Python 3.11.7 (use project virtual environment)
- UI Framework: Gradio for web interfaces
- Image/Video Processing: OpenCV, PIL/Pillow, moviepy
- AI Integration: LM Studio, Ollama API calls
- Dependency Management: uv (preferred), pip as fallback
- Virtual Environment: Always use `.venv` from project root
- **Unknown Packages**: When encountering unfamiliar packages, check the `.venv` directory in this project for documentation and examples

## Running Code
- **Do NOT create .bat batch scripts** for running applications
- Use the virtual environment Python executable directly with full paths
- Format: `J:/Ai_visual_processing_tools/.venv/Scripts/python.exe "j:/Ai_visual_processing_tools/<relative_path_to_script>"`
- Example: `J:/Ai_visual_processing_tools/.venv/Scripts/python.exe "j:/Ai_visual_processing_tools/其他/AI 应用/lmstudio_chat_ui.py"`

## Code Style
- **Type Hints**: Required for all function signatures and class attributes
- **Logging**: Use `logging` module instead of print() in production code
- **Error Handling**: Try-except with specific exceptions, log errors with context
- **Naming Conventions**: 
  - Functions/variables: snake_case
  - Classes: PascalCase
  - Constants: UPPER_CASE


- **UI Tools**: Web UI tools should follow consistent event handler pattern
- **Config Files**: Use `config.ini` format, UTF-8 encoding
- **Module Separation**: business logic / ui handlers / utilities

## AI Integration Patterns
- LM Studio/Ollama API calls: implement retry with exponential backoff
- Async operations where possible for UI responsiveness
- Validate API responses before processing data
- Cache frequently used AI results when appropriate

## File Operations
- Use `pathlib.Path` for all path operations (cross-platform compatibility)
- Always check file existence before read/write operations
- Handle encoding explicitly: UTF-8 for text files, binary mode for images/videos
- Log file operation failures with full traceback

## UI Development Guidelines
- Separate event handlers into dedicated modules (`ui_event_handlers.py`)
- Use consistent styling defined in `styles.py`
- Implement proper error feedback to users via Gradio components
- Clean up temporary files after processing completes

## Testing & Debugging
- **Test Every Function**: After writing a function, immediately test it to verify functionality
- Add logging at key decision points for troubleshooting
- Use environment variables for configuration (API keys, paths)
- Keep sample data in repository for quick testing
