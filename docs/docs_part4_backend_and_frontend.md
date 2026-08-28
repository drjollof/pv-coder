# PV-Coder Documentation — Part 4: Backend API, Data Models & Frontend

---

## 4.1 The Data Models — `src/pv/case_schema.py`

Before explaining the API, you need to understand the data contract — the exact shape of the data that flows through the system.

We use **Pydantic** for our data models. Pydantic is a Python library for data validation using type hints. When you define a Pydantic model, it automatically validates incoming data, converts types where possible, and raises clear errors if required fields are missing or have wrong types.

### `NormalizedEvent` (Lines 4–15)

This represents one single adverse event that was extracted and coded from a narrative. Here is every field explained:

| Field | Type | Description |
|---|---|---|
| `effect_text` | `str` | The raw verbatim text extracted from the narrative (e.g., "really bad headache") |
| `meddra_pt` | `str` | The official MedDRA Preferred Term that was matched (e.g., "Headache") |
| `meddra_pt_id` | `str` | The numeric MedDRA ID (e.g., "10019211") |
| `confidence_score` | `float` | FAISS inner-product similarity score from 0.0 to 1.0 |
| `review_status` | `str` | Either `"Auto-coded"` (high confidence) or `"Human Review"` (low confidence or ambiguous) |
| `top_candidates` | `list[dict]` | The top 3 MedDRA matches with their scores — shown to the human reviewer |
| `suspected_drugs` | `list[str]` | Names of drugs the EventBuilder linked to this specific adverse event |
| `is_serious` | `bool` | Whether *this specific event* triggered a seriousness criterion |
| `is_speculated` | `bool` | Whether the event was mentioned speculatively (e.g., "may cause") |
| `causality` | `Optional[str]` | The investigator's explicit causality statement (e.g., "possibly related"), if extracted |
| `outcome` | `Optional[str]` | The patient outcome (e.g., "recovered", "ongoing"), if extracted |

### `PharmacovigilanceCase` (Lines 17–21)

The top-level container for one complete case report:

| Field | Type | Description |
|---|---|---|
| `case_id` | `str` | Unique identifier (assigned by API, e.g., "CASE-1" or "BATCH-007") |
| `narrative` | `str` | The original raw narrative text that was submitted |
| `events` | `list[NormalizedEvent]` | All adverse events extracted from this narrative |
| `is_serious_case` | `bool` | `True` if ANY single event in the case has `is_serious=True` |

The `is_serious_case` flag on the case level is derived from the event level: `any(e.is_serious for e in normalized_events)`. Even if 9 events are non-serious but 1 is serious, the entire case is flagged — because legally, the case must be treated as a serious case.

---

## 4.2 The FastAPI Backend — `server/main.py`

### What is FastAPI?

FastAPI is a modern Python web framework for building HTTP APIs. It is built on top of **Starlette** (for async web serving) and **Pydantic** (for data validation). It is called "Fast" because:
1. It is extremely performant (comparable to Node.js and Go).
2. It auto-generates documentation (available at `http://localhost:8000/docs`).

When you run `uvicorn server.main:app --reload --port 8000`, you are telling `uvicorn` (the ASGI server) to load the `app` object from `server/main.py` and serve it on port 8000.

### CORS Middleware (Lines 26–32)

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development
    ...
)
```

**CORS (Cross-Origin Resource Sharing)** is a browser security feature. By default, a browser will block a web page from making HTTP requests to a *different domain* than the one it was loaded from. Since our React app is served from `http://localhost:5173` and our API is at `http://localhost:8000`, they are technically "different origins." Without CORS middleware, every API call would fail with a browser security error. This middleware tells the browser "yes, this API intentionally accepts requests from any origin."

In production, you would change `allow_origins=["*"]` to `allow_origins=["https://your-real-domain.com"]` for security.

### The Lazy Loading Pattern — `get_builder()` (Lines 37–45)

```python
_builder = None  # Global instance, starts as None

def get_builder() -> CaseBuilder:
    global _builder
    if _builder is None:
        _builder = CaseBuilder(dict_path, faiss_index_path=faiss_path)
    return _builder
```

This is a critical design decision. Loading all the AI models (ONNX NER, SapBERT, FAISS index) takes approximately 10–15 seconds and requires several gigabytes of RAM. If we did this at import time (when the server starts), the server would hang for 15 seconds before it could answer any request.

With lazy loading, the server starts *instantly*. The first time a user hits the `/api/analyze` endpoint, `get_builder()` is called, sees that `_builder is None`, and triggers the 15-second initialization. Every subsequent call finds `_builder` already initialized and returns it instantly.

The `global _builder` declaration inside the function tells Python that when we assign to `_builder`, we mean the module-level variable, not a local variable.

### `POST /api/analyze` (Lines 51–55)

The primary single-case processing endpoint.

**Request body:**
```json
{
  "narrative": "The patient took aspirin and developed a headache.",
  "case_id": "CASE-1"
}
```

**Response:** A complete `PharmacovigilanceCase` JSON object.

The endpoint is declared with `response_model=PharmacovigilanceCase`. This tells FastAPI to:
1. Validate the returned Python object against the Pydantic model.
2. Automatically serialize it to JSON using the model's field definitions.
3. Include the schema in the auto-generated API documentation.

### `GET /api/examples` (Lines 57–70)

Reads `data/test_narratives.md` from disk and parses it into a list of individual narrative strings. The parsing logic:

```python
blocks = re.split(r'\n\d+\.\s', '\n' + content)
```

This regular expression splits the file on lines that start with a number followed by a period (e.g., `"1. "`, `"2. "`). Each numbered block in the markdown file is one example narrative. It then strips blank blocks and any blocks that start with `"Section"` (which are headers in the test data file, not narratives).

### `POST /api/batch` (Lines 72–94)

The batch processing endpoint. It accepts a multipart file upload:

```python
async def batch_process(file: UploadFile = File(...))
```

`UploadFile` is FastAPI's way of receiving file uploads. The `await file.read()` call is **asynchronous** — the `async` keyword means Python can handle other requests while waiting for the file to be fully received. Once the file bytes are in memory, `io.BytesIO(content)` wraps them in a file-like object so Pandas can read them with `pd.read_csv()`.

The function iterates over every row, calls `builder.process()` on each narrative, and appends the result. The list of `PharmacovigilanceCase` objects is returned and FastAPI automatically serializes it to a JSON array.

### `generate_xml_string(case)` (Lines 96–122)

A helper function (not an endpoint itself) that converts a `PharmacovigilanceCase` into an E2B(R3) XML string.

It uses Python's built-in `xml.etree.ElementTree` library:
- `ET.Element("ichicsr", lang="en")` creates the root XML element with an attribute.
- `ET.SubElement(parent, "tagname")` creates a child element under the parent.
- `ET.SubElement(...)`.text assigns text content to an element.
- Finally, `ET.tostring(root, encoding='utf-8', method='xml').decode()` serializes the entire tree to a string.

The E2B seriousness code: `"1"` means serious, `"2"` means non-serious. This is the ICH-defined numeric coding.

### `POST /api/export/batch/xml-zip` (Lines 124–136)

Takes a list of `PharmacovigilanceCase` objects, generates one XML file per case, and bundles them into a ZIP archive.

```python
temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
    for case in cases:
        xml_str = generate_xml_string(case)
        zipf.writestr(f"{case.case_id}.xml", xml_str)
```

`tempfile.NamedTemporaryFile(delete=False)` creates a temporary file on disk that persists after the `with` block closes (because `delete=False`). `zipfile.ZIP_DEFLATED` is the compression algorithm — it makes the ZIP smaller. `zipf.writestr()` writes an in-memory string directly into the ZIP without ever needing to create individual XML files on disk.

`FileResponse` tells FastAPI to stream the file from disk back to the client browser, which triggers a download.

### `POST /api/export/pdf` (Lines 143–237)

Generates a formatted PDF using the `fpdf` (FPDF2) library. FPDF works by drawing elements on a virtual page:

- `pdf.add_page()` — adds a new blank page.
- `pdf.set_font("Arial", 'B', 18)` — sets the font (Bold Arial at size 18).
- `pdf.set_text_color(R, G, B)` — sets the text color using RGB values.
- `pdf.set_fill_color(R, G, B)` — sets the background fill color.
- `pdf.cell(width, height, text, ...)` — draws a single-line cell with text.
- `pdf.multi_cell(width, height, text)` — draws text that automatically wraps across multiple lines.

The `.encode('latin-1', 'replace').decode('latin-1')` step is a crucial workaround. The basic Arial font in FPDF only supports latin-1 characters. If the narrative contains a Unicode character (like an em-dash or a non-ASCII letter), FPDF would crash. The encode/decode with `'replace'` substitutes unsupported characters with a `?` rather than crashing.

For the seriousness banner, we use a conditional fill color:
- Red background (`254, 226, 226`) and red text (`220, 38, 38`) for Serious cases.
- Green background (`209, 250, 229`) and green text (`5, 150, 105`) for Non-Serious cases.

---

## 4.3 The React Frontend — `client/src/`

### Vite — The Build Tool

The frontend was bootstrapped with **Vite** (`npm create vite@latest`). Vite is a modern development server and build tool that:
- Serves your React code locally using native ES modules (no bundling during development — extremely fast hot reloading).
- Bundles the code for production using Rollup when you run `npm run build`.

When you run `npm run dev`, Vite starts the dev server on `http://localhost:5173`.

### `client/src/App.jsx` — The Complete Application

The entire React application is in a single `App.jsx` file. Here is a breakdown of every piece of state and every component.

### Root `App()` Component

The root component manages only the tab navigation:
```javascript
const [activeTab, setActiveTab] = useState('single')
```

It renders the header, the two tab buttons ("Single Intake" / "Batch Upload"), and a "How to Use" guide section. The active tab determines which component is rendered in the body.

### `SingleIntake()` Component

This is the main NLP interface. It manages several pieces of state:

| State Variable | Type | Purpose |
|---|---|---|
| `narrative` | `string` | The text currently typed in the textarea |
| `loading` | `boolean` | Controls the spinner visibility during API call |
| `result` | `object \| null` | The `PharmacovigilanceCase` JSON returned from the API |
| `error` | `string` | Error message to display if the API call fails |
| `showJson` | `boolean` | Toggles the raw JSON debug view |
| `corrections` | `object` | Stores the human reviewer's MedDRA code selections (keyed by event index) |
| `manualInputs` | `object` | Stores typed manual MedDRA PT and ID when the reviewer selects "Reject All / Other" |
| `examples` | `array` | The list of example narratives loaded from the API |

**`useEffect` for examples (Lines ~57–65):**
```javascript
useEffect(() => {
    fetch('http://localhost:8000/api/examples')
        .then(res => res.json())
        .then(data => setExamples(data.examples || []))
}, [])
```
The `useEffect` with an empty dependency array `[]` runs exactly once, when the component first mounts. It fetches the examples from the API and stores them in state. This is the standard React pattern for loading data on component initialization.

**`handleAnalyze()` (Lines ~67–87):**
Uses the browser's built-in `fetch()` API to make a POST request to `/api/analyze`. The request body is JSON (narrative + case_id). The response is parsed as JSON and stored in `result`. If anything goes wrong, the error message is stored in `error` state for display.

**`handleCorrection(eventIdx, selectedId, selectedPt)`:**
Called when the user clicks one of the radio buttons in the Human Review panel. It stores the selected MedDRA code in the `corrections` object, keyed by the event's index: `corrections[0]`, `corrections[1]`, etc.

**`handleManualInputChange(eventIdx, field, value)`:**
Called when the user types in the manual input boxes. It updates both `manualInputs` (for the display) and `corrections` (for the final state) simultaneously.

**The Result Display:**
After `result` is set, the component renders:
1. A Serious/Non-Serious banner using a `<CheckCircle>` or `<AlertTriangle>` icon from lucide-react.
2. An events table showing every extracted `NormalizedEvent` with its MedDRA code and review status indicator.
3. The Human-in-the-Loop panel (only if `reviewEvents.length > 0`).
4. An export action bar with buttons for PDF, XML, and JSON exports.

**PDF Export:**
```javascript
const res = await fetch('http://localhost:8000/api/export/pdf', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(result)
})
const blob = await res.blob()
const url = window.URL.createObjectURL(blob)
const a = document.createElement('a')
a.href = url
a.download = `${result.case_id}_report.pdf`
document.body.appendChild(a)
a.click()
window.URL.revokeObjectURL(url)
```

This is the standard browser trick for triggering a file download from JavaScript. `res.blob()` reads the response as a binary Blob. `URL.createObjectURL(blob)` creates a temporary in-memory URL for that blob. We create a hidden `<a>` element, set its `href` to that URL, programmatically click it, and then immediately clean up by revoking the URL and removing the element.

### `BatchUpload()` Component

Manages the batch workflow through two visual states:
1. **Upload state** (`results === null`): Shows the file drop area and Process button.
2. **Dashboard state** (`results !== null`): Shows the metrics cards, export buttons, and preview table.

**`handleUpload()`:** Uses `FormData` to package the CSV file. `FormData` is the browser's built-in way to submit files in a multipart/form-data request, which is what FastAPI's `UploadFile` expects.

**`exportCSV()`:** Builds the CSV file entirely in JavaScript in the browser. It creates a 2D array of rows (the header row + one row per event), joins each row with commas, joins all rows with newlines, and creates a `data:text/csv;charset=utf-8,` data URI. This does not require a round-trip to the server at all.

**`exportXMLZip()`:** Unlike the CSV export (which is done in-browser), the XML ZIP requires a round-trip to the server because generating compliant E2B XML is complex server logic. It sends the entire `results` JSON array back to `/api/export/batch/xml-zip` and receives a ZIP blob in return.

---

## 4.4 The CSS Design System — `client/src/index.css`

The entire visual design lives in a single Vanilla CSS file. We deliberately avoided CSS frameworks (like Tailwind or Bootstrap) to maintain complete control over the styling.

**CSS Custom Properties (Variables) at `:root`:**

All colors, spacings, and border radii are defined as CSS variables in the `:root` block:
```css
--bg-primary: #0f1117;        /* deepest dark background */
--bg-secondary: #1a1d27;      /* card background */
--bg-tertiary: #242736;       /* input/table background */
--accent-primary: #7c3aed;    /* purple - main brand color */
--accent-secondary: #2563eb;  /* blue - secondary actions */
--warning: #f59e0b;           /* amber - review needed, serious */
--warning-bg: rgba(245, 158, 11, 0.1);
--success: #10b981;           /* emerald - auto-coded, non-serious */
```

Changing the color scheme of the entire application requires only changing these variables in one place.

**Glassmorphism Effect:**
Several panels use the "glassmorphism" design pattern:
```css
background: rgba(26, 29, 39, 0.8);
backdrop-filter: blur(10px);
border: 1px solid rgba(255, 255, 255, 0.06);
```
The `backdrop-filter: blur()` creates the frosted-glass look by blurring whatever is rendered behind the element.

**The `slideIn` Animation:**
```css
@keyframes slideIn {
    from { opacity: 0; transform: translateY(20px); }
    to   { opacity: 1; transform: translateY(0); }
}
```
This animation is applied to the results section every time new content appears. It creates a subtle upward fade-in motion that signals to the user that content has changed.

---

## 4.5 Running & Deploying

### Local Development

Run in two separate terminals:

**Terminal 1 (Backend):**
```bash
# From the pv-coder/ root directory
uvicorn server.main:app --reload --port 8000
```

**Terminal 2 (Frontend):**
```bash
cd client
npm run dev
```

Open `http://localhost:5173` in your browser.

### Production Deployment

1. **Backend:** Containerize with Docker. Deploy to a service that supports containers with at least 8GB RAM (AWS Fargate, Google Cloud Run, Azure Container Apps). Update the CORS `allow_origins` to your real frontend domain.

2. **Frontend:** Run `npm run build` in `client/`. This produces a `dist/` folder of optimized static files. Deploy to Vercel, Netlify, AWS S3 + CloudFront, or any static hosting. Before building, update all `http://localhost:8000` URLs in `App.jsx` to point to your production backend URL.
