import gradio as gr
import spaces
from fastapi import FastAPI
from server.main import app as fastapi_app

# Create a dummy Gradio interface that satisfies HF Zero GPU requirement
@spaces.GPU
def dummy():
    return "PV-Coder API is running on Hugging Face Spaces!"

iface = gr.Interface(
    fn=dummy, 
    inputs=None, 
    outputs="text",
    title="PV-Coder Backend API",
    description="This space hosts the FastAPI backend for PV-Coder."
)

# Mount the FastAPI app to Gradio
app = gr.mount_gradio_app(fastapi_app, iface, path="/")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
