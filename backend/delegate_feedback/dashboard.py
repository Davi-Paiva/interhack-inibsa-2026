from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

try:
    from .service import (
        ACTION_TAKEN_OPTIONS,
        ALERT_VALIDITY_OPTIONS,
        BUSINESS_OUTCOME_OPTIONS,
        RESOLUTION_STATUS_OPTIONS,
        DelegateFeedbackService,
    )
    from ..global_prioritization.service import GlobalPrioritizationService
except ImportError:
    from backend.delegate_feedback.service import (
        ACTION_TAKEN_OPTIONS,
        ALERT_VALIDITY_OPTIONS,
        BUSINESS_OUTCOME_OPTIONS,
        RESOLUTION_STATUS_OPTIONS,
        DelegateFeedbackService,
    )
    from backend.global_prioritization.service import GlobalPrioritizationService


BASE_DIR = Path(__file__).resolve().parents[2]


def _queue_frame(service: DelegateFeedbackService, mode: str) -> pd.DataFrame:
    rows = service.load_global_queue(mode)
    if not rows:
        return pd.DataFrame()
    frame = pd.DataFrame(rows)
    for column in ("process_on_date", "suppression_until"):
        if column in frame.columns:
            frame[column] = pd.to_datetime(frame[column], errors="coerce")
    return frame


def _feedback_frame(service: DelegateFeedbackService, mode: str) -> pd.DataFrame:
    frame = service.load_feedback_frame(mode)
    if frame.empty:
        return frame
    for column in ("resolved_at", "created_at"):
        frame[column] = pd.to_datetime(frame[column], errors="coerce")
    return frame.sort_values("resolved_at", ascending=False)


def _queue_count_from_json(path: Path) -> int:
    if not path.exists():
        return 0
    payload = json.loads(path.read_text(encoding="utf-8"))
    return len(payload) if isinstance(payload, list) else 0


def main() -> None:
    st.set_page_config(page_title="Delegate Feedback Dashboard", layout="wide")
    st.title("Delegate Feedback Dashboard")

    mode = "daily"
    st.sidebar.caption("Delegate view is daily-only. Historical remains internal for training.")
    service = DelegateFeedbackService(project_root=BASE_DIR)
    queue_service = GlobalPrioritizationService(project_root=BASE_DIR)
    queue = _queue_frame(service, mode)
    feedback = _feedback_frame(service, mode)
    queue_path = BASE_DIR / "backend" / "global_prioritization" / "output" / mode / "global_alert_queue.json"
    full_queue_path = BASE_DIR / "backend" / "global_prioritization" / "output" / mode / "global_alert_queue_full.json"
    st.sidebar.subheader("Daily demo controls")
    st.sidebar.caption("Use these controls to alternate between an empty public daily queue and a simulated first run.")

    public_count = _queue_count_from_json(queue_path)
    full_count = _queue_count_from_json(full_queue_path)
    st.sidebar.write(
        {
            "public_daily_alerts": public_count,
            "internal_full_snapshot": full_count,
        }
    )

    if st.sidebar.button("Mark snapshot as seen", use_container_width=True):
        outputs = queue_service.mark_current_daily_snapshot_as_seen(mode)
        st.sidebar.success("Daily queue set to 0 new alerts.")
        st.sidebar.caption(", ".join(str(path) for path in outputs.values()))
        st.rerun()

    if st.sidebar.button("Simulate first run", use_container_width=True):
        outputs = queue_service.simulate_daily_first_run(mode)
        st.sidebar.success("Daily queue reset to show the current snapshot as new alerts.")
        st.sidebar.caption(", ".join(str(path) for path in outputs.values()))
        st.rerun()

    if queue.empty:
        if queue_path.exists():
            st.info("No new daily alerts in the latest run.")
            if full_count:
                st.caption(f"Internal full snapshot still has {full_count} active alerts, but none are new vs the previous run.")
        else:
            st.warning("No global alert queue found for this mode yet. Run the pipeline first.")
            st.caption(queue_path)
        return

    st.caption(f"Queue source: {queue_path}")

    open_alerts = int(len(queue))
    suppressed = int(queue["suppression_until"].notna().sum()) if "suppression_until" in queue.columns else 0
    feedback_count = int(len(feedback))
    left, middle, right = st.columns(3)
    left.metric("Alerts in queue", open_alerts)
    middle.metric("Suppressed by feedback", suppressed)
    right.metric("Feedback records", feedback_count)

    if "queue_rank" in queue.columns:
        queue = queue.sort_values("queue_rank", ascending=True)

    labels = []
    for row in queue.to_dict(orient="records"):
        labels.append(
            f"#{row.get('queue_rank', '-')}: {row.get('canonical_variant', '')} | "
            f"{row.get('customer_id', '')} / {row.get('product_id', '')}"
        )
    selected_label = st.selectbox("Select alert", options=labels, index=0)
    selected_alert = queue.to_dict(orient="records")[labels.index(selected_label)]

    summary_col, context_col = st.columns([1.2, 1.0])
    with summary_col:
        st.subheader("Alert summary")
        st.write(
            {
                "alert_id": selected_alert.get("global_alert_id"),
                "variant": selected_alert.get("canonical_variant"),
                "customer_id": selected_alert.get("customer_id"),
                "product_id": selected_alert.get("product_id"),
                "base_priority_band": selected_alert.get("global_priority_band"),
                "feedback_adjusted_priority": selected_alert.get("feedback_adjusted_priority"),
                "process_on_date": str(selected_alert.get("process_on_date", "")),
                "suppression_until": str(selected_alert.get("suppression_until", "")),
            }
        )
        st.markdown("**Motivo de la alerta**")
        st.write(selected_alert.get("alert_reason_summary") or "No reason summary available yet.")
        st.markdown("**Accion recomendada**")
        st.write(selected_alert.get("recommended_action") or "No recommended action.")
        st.markdown("**Hint historico**")
        st.write(selected_alert.get("delegate_hint") or "No historical hint yet.")

    with context_col:
        st.subheader("Quick feedback")
        with st.form(key="delegate-feedback-form", clear_on_submit=False):
            delegate_id = st.text_input("Delegate ID", value="")
            resolution_status = st.selectbox("Resolution status", RESOLUTION_STATUS_OPTIONS, index=0)
            alert_validity = st.selectbox("Alert validity", ALERT_VALIDITY_OPTIONS, index=0)
            action_taken = st.selectbox("Action taken", ACTION_TAKEN_OPTIONS, index=0)
            business_outcome = st.selectbox("Business outcome", BUSINESS_OUTCOME_OPTIONS, index=0)
            root_cause_options = service.root_cause_options(str(selected_alert.get("canonical_variant", "")))
            root_cause = st.selectbox("Root cause", root_cause_options, index=0)
            free_note = st.text_area("Free note", max_chars=280, placeholder="Short optional note for future learning.")
            submitted = st.form_submit_button("Save feedback")

        if submitted:
            if not delegate_id.strip():
                st.error("Delegate ID is required.")
            else:
                paths = service.record_feedback(
                    mode,
                    selected_alert,
                    delegate_id=delegate_id.strip(),
                    resolution_status=resolution_status,
                    alert_validity=alert_validity,
                    action_taken=action_taken,
                    business_outcome=business_outcome,
                    root_cause=root_cause,
                    free_note=free_note,
                    rebuild_policy=True,
                )
                st.success("Feedback saved.")
                st.caption(", ".join(str(path) for path in paths.values()))

    st.subheader("Current queue")
    display_columns = [
        column
        for column in [
            "queue_rank",
            "canonical_variant",
            "customer_id",
            "product_id",
            "global_priority_band",
            "feedback_adjusted_priority",
            "process_day_bucket",
            "repeat_alert_count_30d",
            "last_delegate_outcome",
            "suppression_until",
            "alert_reason_summary",
        ]
        if column in queue.columns
    ]
    st.dataframe(queue[display_columns], use_container_width=True, hide_index=True)

    st.subheader("Recent feedback")
    if feedback.empty:
        st.info("No feedback saved yet.")
    else:
        st.dataframe(
            feedback[
                [
                    "resolved_at",
                    "global_alert_id",
                    "delegate_id",
                    "resolution_status",
                    "alert_validity",
                    "action_taken",
                    "business_outcome",
                    "root_cause",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )


if __name__ == "__main__":
    main()
