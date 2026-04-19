"""RepoCompass Streamlit UI."""
import streamlit as st
import json
import sys
import tempfile
import hashlib
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.pipelines.analysis import RepoCompassPipeline
from app import config

st.set_page_config(page_title="RepoCompass", page_icon="🧭", layout="wide")

st.title("🧭 RepoCompass")
st.caption("Multi-Agent RAG for Codebase Architecture Explainers & API Mapping")

# Initialize pipeline in session state
if "pipeline" not in st.session_state:
    st.session_state.pipeline = RepoCompassPipeline()

if "result" not in st.session_state:
    st.session_state.result = None

if "repo_id" not in st.session_state:
    st.session_state.repo_id = None

# ─── Sidebar: Upload ───
with st.sidebar:
    st.header("📁 Repository Input")

    input_mode = st.radio("Input mode", ["Upload ZIP", "Local Path"])

    repo_source = None
    repo_id = None

    if input_mode == "Upload ZIP":
        uploaded = st.file_uploader("Upload repository ZIP", type=["zip"])
        if uploaded:
            content = uploaded.read()
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
            tmp.write(content)
            tmp.close()
            repo_source = Path(tmp.name)
            repo_id = hashlib.md5(content).hexdigest()[:12]
    else:
        path_str = st.text_input("Local repository path")
        if path_str and Path(path_str).exists():
            repo_source = Path(path_str)
            repo_id = Path(path_str).name

    if repo_source and st.button("🔍 Analyze Repository", type="primary"):
        with st.spinner("Running full analysis pipeline..."):
            try:
                st.session_state.result = st.session_state.pipeline.run(repo_source, repo_id)
                st.session_state.repo_id = st.session_state.result.repo_id
                st.success("Analysis complete!")
            except Exception as e:
                st.error(f"Analysis failed: {e}")

# ─── Main Tabs ───
result = st.session_state.result

tab_arch, tab_api, tab_flow, tab_risk, tab_qa = st.tabs([
    "🏗️ System Map", "🔌 API Map", "🔄 Call-Flow", "⚠️ Risk Notes", "❓ Ask-Repo Q&A"
])

with tab_arch:
    st.header("System / Architecture Explainer")
    if result:
        st.subheader("Summary")
        st.write(result.architecture.summary)

        if result.architecture.components:
            st.subheader("Components")
            for comp in result.architecture.components:
                conf_color = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(comp.confidence, "⚪")
                st.markdown(f"**{conf_color} {comp.name}** — {comp.role}")
                if comp.uncertainty_note:
                    st.caption(f"⚠️ {comp.uncertainty_note}")
                with st.expander("Evidence"):
                    for ev in comp.evidence:
                        st.code(f"{ev.file_path}:{ev.line_start}-{ev.line_end}")

        if result.architecture.system_observations:
            st.subheader("System Observations")
            for obs in result.architecture.system_observations:
                conf_color = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(obs.confidence, "⚪")
                st.markdown(f"{conf_color} {obs.claim}")
                if obs.uncertainty_note:
                    st.caption(f"⚠️ {obs.uncertainty_note}")
        else:
            if not result.architecture.components:
                st.info("No architecture components identified. (LLM generation may not be configured.)")
    else:
        st.info("Upload a repository to see the architecture explainer.")

with tab_api:
    st.header("API Endpoint Inventory")
    if result and result.api_map.endpoints:
        st.caption(f"Framework: **{result.api_map.framework}** | Endpoints found: **{len(result.api_map.endpoints)}**")
        for ep in result.api_map.endpoints:
            conf_color = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(ep.confidence, "⚪")
            method_color = {"GET": "🔵", "POST": "🟠", "PUT": "🟣", "DELETE": "🔴", "PATCH": "🟡"}.get(ep.method, "⚪")
            st.markdown(f"{conf_color} **{method_color} `{ep.method}`** `{ep.route}`")
            if ep.handler_name:
                st.caption(f"Handler: `{ep.handler_name}`" + (f" at `{ep.handler_location.file_path}:{ep.handler_location.line_start}`" if ep.handler_location else ""))
            if ep.uncertainty_note:
                st.caption(f"⚠️ {ep.uncertainty_note}")
            with st.expander("Evidence"):
                for ev in ep.evidence:
                    st.code(f"{ev.file_path}:{ev.line_start}-{ev.line_end}")
    else:
        st.info("Upload a repository to see the API map.")

with tab_flow:
    st.header("Call-Flow Summary")
    if result and result.callflow.flows:
        for flow in result.callflow.flows:
            conf_color = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(flow.overall_confidence, "⚪")
            st.subheader(f"{conf_color} {flow.name}")
            st.caption(f"Entrypoint: `{flow.entrypoint}`")
            if flow.uncertainty_note:
                st.caption(f"⚠️ {flow.uncertainty_note}")
            for step in flow.steps:
                st.markdown(f"**Step {step.step_number}:** {step.description}")
                if step.uncertainty_note:
                    st.caption(f"⚠️ {step.uncertainty_note}")
    else:
        if result:
            st.info("No call flows identified. (LLM generation may not be configured.)")
        else:
            st.info("Upload a repository to see the call-flow summary.")

with tab_risk:
    st.header("Risk Notes")
    if result and result.risk_notes.risk_notes:
        for note in result.risk_notes.risk_notes:
            cat_icon = {"security": "🔒", "correctness": "🐛", "maintainability": "🔧",
                        "ambiguity": "❓", "configuration": "⚙️"}.get(note.category, "⚠️")
            conf_color = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(note.confidence, "⚪")
            st.markdown(f"### {cat_icon} {conf_color} {note.title}")
            st.write(note.description)
            st.caption(f"Why it matters: {note.why_it_matters}")
            if note.requires_human_review:
                st.warning("👁️ Requires human review")
            with st.expander("Evidence"):
                for ev in note.evidence:
                    st.code(f"{ev.file_path}:{ev.line_start}-{ev.line_end}")
    else:
        if result:
            st.success("No risk notes generated — all extracted items have high confidence.")
        else:
            st.info("Upload a repository to see risk notes.")

with tab_qa:
    st.header("Ask-Repo Q&A")
    repo_id_val = st.session_state.get("repo_id")
    if repo_id_val:
        question = st.text_input("Ask a question about the repository:")
        if question and st.button("Ask"):
            with st.spinner("Retrieving evidence and generating answer..."):
                answer = st.session_state.pipeline.ask_repo(repo_id_val, question)
            if answer.insufficient_evidence:
                st.warning("Insufficient evidence to answer this question.")
                if answer.uncertainty_note:
                    st.caption(answer.uncertainty_note)
            else:
                st.write(answer.answer)
                conf_color = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(answer.confidence, "⚪")
                st.caption(f"Confidence: {conf_color} {answer.confidence}")
                if answer.evidence:
                    with st.expander("Evidence"):
                        for ev in answer.evidence:
                            st.code(f"{ev.file_path}:{ev.line_start}-{ev.line_end}")
    else:
        st.info("Analyze a repository first, then ask questions about it.")

# ─── Stats ───
if result and result.stats:
    with st.sidebar:
        st.header("📊 Pipeline Stats")
        for key, val in result.stats.items():
            st.metric(key, f"{val}s" if isinstance(val, float) else str(val))
        if result.chunks_count:
            st.metric("Chunks indexed", result.chunks_count)
        if result.api_map.endpoints:
            st.metric("Endpoints found", len(result.api_map.endpoints))
