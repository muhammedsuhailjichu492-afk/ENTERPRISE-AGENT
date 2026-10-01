
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest


class MLAgent:
    name = "ml_agent"

    def analyze(self, records: list[dict], metric: str) -> dict:
        df = pd.DataFrame(records)
        if df.empty or metric not in df.columns:
            return {
                "anomalies": [],
                "anomaly_rate": 0.0,
                "trend": None,
                "note": "Insufficient data for ML analysis.",
            }

        numeric_df = df.select_dtypes(include=[np.number]).copy()
        numeric_df = numeric_df.drop(columns=[c for c in ("id",) if c in numeric_df.columns])
        if metric not in numeric_df.columns or len(numeric_df) < 5:
            return {
                "anomalies": [],
                "anomaly_rate": 0.0,
                "trend": None,
                "note": "Not enough numeric history (need >= 5 records) for anomaly detection.",
            }

        numeric_df = numeric_df.fillna(numeric_df.mean(numeric_only=True))

        model = IsolationForest(
            n_estimators=150,
            contamination="auto",
            random_state=42,
        )
        labels = model.fit_predict(numeric_df)  # -1 = anomaly, 1 = normal
        scores = model.decision_function(numeric_df)  # lower = more anomalous

        anomalies = []
        for idx, (label, score) in enumerate(zip(labels, scores)):
            if label == -1:
                row = df.iloc[idx].to_dict()
                anomalies.append({
                    "index": int(idx),
                    "row": {k: (v if not isinstance(v, (np.integer, np.floating)) else float(v))
                            for k, v in row.items()},
                    "anomaly_score": round(float(score), 4),
                })

        anomaly_rate = round(len(anomalies) / len(df), 4)
        trend = self._trend(df[metric])

        # Keep the most severe anomalies only, to stay prompt-friendly downstream
        anomalies.sort(key=lambda a: a["anomaly_score"])
        top_anomalies = anomalies[:5]

        return {
            "anomalies": top_anomalies,
            "anomaly_count": len(anomalies),
            "anomaly_rate": anomaly_rate,
            "trend": trend,
        }

    @staticmethod
    def _trend(series: pd.Series) -> dict | None:
        values = pd.to_numeric(series, errors="coerce").dropna().to_numpy()
        if len(values) < 4:
            return None

        x = np.arange(len(values))
        slope, intercept = np.polyfit(x, values, 1)
        forecast_next = float(slope * len(values) + intercept)
        pct_change_window = 0.0
        first_half_mean = values[: len(values) // 2].mean()
        second_half_mean = values[len(values) // 2:].mean()
        if first_half_mean != 0:
            pct_change_window = round(float((second_half_mean - first_half_mean) / abs(first_half_mean)) * 100, 2)

        direction = "flat"
        if slope > 0.01 * (abs(values.mean()) + 1e-6):
            direction = "increasing"
        elif slope < -0.01 * (abs(values.mean()) + 1e-6):
            direction = "decreasing"

        return {
            "slope": round(float(slope), 4),
            "direction": direction,
            "forecast_next_period": round(forecast_next, 3),
            "pct_change_first_vs_second_half": pct_change_window,
        }
