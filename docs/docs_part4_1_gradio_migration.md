# PV-Coder Documentation — Part 4.1: Gradio Headless Architecture Migration

---

## 4.1.1 The API Migration (Farewell FastAPI)

Originally, PV-Coder's backend was powered by **FastAPI** (`server/main.py`). The React frontend communicated with it using standard HTTP `fetch()` requests and REST endpoints (e.g., `POST /api/analyze`). 

However, to deploy the backend to a **Hugging Face ZeroGPU Space**, a fundamental architectural shift was required. Hugging Face's ZeroGPU infrastructure exclusively supports applications built with their proprietary **Gradio** framework. Standard FastAPI endpoints cannot hook into the ZeroGPU dynamic hardware allocation.

To solve this, we retired the FastAPI server entirely and migrated to a **Gradio Headless API** architecture (`app.py`).

---

## 4.1.2 Gradio as a Headless Backend (`app.py`)

Gradio is traditionally used to build simple graphical user interfaces (GUIs) for machine learning models. However, we are using Gradio in **"Headless Mode"**—we do not use any of its UI components. Instead, we use it purely as a backend server that our React frontend talks to.

### The `@spaces.GPU` Decorator

The entire reason for this migration is to leverage this single decorator:

```python
import spaces

@spaces.GPU
def analyze_api(narrative: str, case_id: str) -> str:
    # ... NLP pipeline execution ...
```

When a function is decorated with `@spaces.GPU`, Hugging Face's infrastructure dynamically routes the execution of that specific function to an NVIDIA A100 GPU. It automatically moves the PyTorch models from CPU RAM to VRAM just for the duration of the function call, and releases the GPU immediately after. This allows Hugging Face to share GPUs across thousands of applications.

### The Gradio Endpoint Definition

Instead of defining REST endpoints, Gradio APIs are defined by binding Python functions to Gradio invisible components:

```python
with gr.Blocks() as demo:
    # Invisible components for input/output routing
    narrative_in = gr.Textbox(visible=False)
    case_id_in = gr.Textbox(visible=False)
    json_out = gr.Textbox(visible=False)
    
    # Binding the function
    btn = gr.Button("Analyze", visible=False)
    btn.click(
        fn=analyze_api,
        inputs=[narrative_in, case_id_in],
        outputs=[json_out],
        api_name="analyze"
    )
```

This creates an endpoint accessible at `/analyze` (or `/api/analyze` depending on the client).

---

## 4.1.3 The Frontend Migration: `@gradio/client`

Because the backend is now a Gradio server, the React frontend (`client/src/App.jsx`) could no longer use standard `fetch()` requests. Gradio utilizes a complex WebSocket communication protocol rather than standard HTTP POSTs.

### The `Client.connect()` Pattern

We installed the official `@gradio/client` npm package. In `App.jsx`, API calls are now executed like this:

```javascript
import { Client } from "@gradio/client";

// Connect to the Gradio WebSocket server
const client = await Client.connect("https://drjollof-pv-coder-api.hf.space");

// Send the inputs matching the order of the Gradio btn.click array
const res = await client.predict("/analyze", [
    narrative, 
    'WEB-' + Math.floor(Math.random()*1000)
]);

// Parse the returned JSON string back into an object
const data = JSON.parse(res.data[0]);
```

---

## 4.1.4 Overcoming the Serialization Barrier (Base64)

Gradio's internal mechanisms have strict requirements for passing complex data types. During the migration, we discovered that passing complex JSON objects or file buffers directly through the Gradio client caused internal parsing errors (`gr.JSON` bugs).

### The Stringification Solution

To make the architecture bulletproof, we adopted a strict **String-Only Transport Protocol** between the React frontend and the Gradio backend.

1. **JSON Data:** Instead of returning Python dictionaries, the Python backend converts the `PharmacovigilanceCase` Pydantic model into a strict JSON string using `json.dumps()`. The React frontend receives this single string and calls `JSON.parse()`.
2. **File Uploads (CSV):** Instead of uploading binary files (which broke the Gradio client), the React frontend reads the CSV file locally, converts it into a **Base64 encoded string**, and sends that string to the backend:

```javascript
// React Frontend: Convert File to Base64
const reader = new FileReader();
reader.readAsDataURL(file);
reader.onload = async () => {
    const base64Data = reader.result.split(',')[1];
    const res = await client.predict("/batch", [base64Data]);
};
```

```python
# Python Backend: Decode Base64 to DataFrame
import base64
import pandas as pd
import io

@spaces.GPU
def batch_process_api(base64_csv: str) -> str:
    csv_bytes = base64.b64decode(base64_csv)
    df = pd.read_csv(io.BytesIO(csv_bytes))
    # ... process rows ...
```

By reducing all communication (text, objects, and files) down to primitive strings, we completely bypassed Gradio's schema validation bugs, resulting in a highly stable, decoupled architecture capable of leveraging advanced GPU hardware.
