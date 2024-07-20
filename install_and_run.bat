
@echo off    
echo Installing Python dependencies...    
pip install requests
pip install pandas
pip install psutil
pip install gradio
pip install scikit-learn

echo Installation complete.

echo Running the application...    
python ollama_interface.py    
pause   