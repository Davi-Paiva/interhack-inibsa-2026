# Signal Fusion & Prioritization

This package turns the outputs from the commodity and technical engines into
ranked, explainable and channel-ready alerts.

## Architecture

- `domain/structures.py`: shared alert contracts, product blocks, priority levels
  and the activation actors from the briefing: `delegado`, `televenta` and
  `marketing_automation`.
- `adapters/artifact_loader.py`: reads processed tables and engine artifacts.
- `alarms/`: one file per alarm type.
- `services/`: prioritization, routing, duplicate suppression, export and
  orchestration.

## Run

From the project root:

```bash
python -m backend.signal_fusion --mode historical --top-n 200
```

Outputs are written to:

```text
backend/signal_fusion/output/<mode>/alerts.json
backend/signal_fusion/output/<mode>/alerts.csv
```

Each alert includes the client, product or family, reason, recommendation,
business priority, expected revenue, target actor and operational deadline.
