import os
import json
import pickle
import logging
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timezone
import numpy as np
import sklearn
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
from sklearn.preprocessing import LabelEncoder
import xgboost as xgb
from app.core.config import settings
from app.schemas.review import TrainingDataRecord
from app.services.ml.dataset import DatasetBuilder

logger = logging.getLogger(__name__)

# Standard Feature Columns in Vector
FEATURE_COLUMNS = [
    "frp",
    "confidence",
    "brightness_temperature",
    "detection_count",
    "active_days",
    "duration_hours",
    "mean_frp",
    "max_frp",
    "frp_std",
    "frp_deviation_ratio",
    "spatial_spread_meters",
    "detection_frequency",
    "temporal_status_code",
    "distance_to_industrial_facility",
    "is_industrial_land",
    "land_cover_code",
    "land_cover_category_code",
    "has_satellite_data",
    "cloud_coverage",
    "ndvi",
    "nbr",
    "ndwi",
    "swir_nir_ratio",
    "burn_scar_detected",
    "persistence_score",
    "recurrence_score",
    "abnormality_score"
]

class MLTrainer:
    """
    Production Machine Learning Training and Evaluation Pipeline.
    Trains XGBoost multi-class classifier on versioned, leakage-free training datasets
    and stores serialized model artifacts with comprehensive evaluation metadata.
    """

    def __init__(
        self,
        registry_dir: str = settings.MODEL_REGISTRY_PATH,
        model_version: str = settings.ACTIVE_MODEL_VERSION
    ):
        self.registry_dir = registry_dir
        self.model_version = model_version
        self.feature_columns = FEATURE_COLUMNS
        self.feature_schema_version = "v2.0"

    def train_and_evaluate(
        self,
        records: Optional[List[TrainingDataRecord]] = None,
        test_size: float = 0.25,
        dataset_version: str = "v1.0",
        random_state: int = 42
    ) -> Dict[str, Any]:
        """
        Executes end-to-end model training, evaluation, and artifact registry saving.
        """
        if not records:
            records = DatasetBuilder.build_dataset(version=dataset_version)

        if len(records) < 4:
            raise ValueError(f"Insufficient training records ({len(records)}); minimum 4 required.")

        # 1. Anti-leakage split
        train_records, test_records, split_meta = DatasetBuilder.get_dataset_split(
            records, test_size=test_size, random_state=random_state
        )

        # 2. Vectorize features & encode target labels
        X_train, y_train_raw = self._vectorize(train_records)
        X_test, y_test_raw = self._vectorize(test_records)

        label_encoder = LabelEncoder()
        # Fit on all possible labels present in dataset
        all_labels = [r.label for r in records]
        label_encoder.fit(all_labels)

        y_train = label_encoder.transform(y_train_raw)
        y_test = label_encoder.transform(y_test_raw)
        classes = [str(c) for c in label_encoder.classes_]

        # 3. Train XGBoost Classifier
        # Native handling of missing values (np.nan) in tree split search
        model = xgb.XGBClassifier(
            n_estimators=50,
            max_depth=4,
            learning_rate=0.1,
            objective="multi:softprob",
            eval_metric="mlogloss",
            random_state=random_state
        )
        model.fit(X_train, y_train)

        # 4. Evaluate on Test Split
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test)

        acc = float(accuracy_score(y_test, y_pred))
        macro_prec = float(precision_score(y_test, y_pred, average="macro", zero_division=0))
        macro_rec = float(recall_score(y_test, y_pred, average="macro", zero_division=0))
        macro_f1 = float(f1_score(y_test, y_pred, average="macro", zero_division=0))

        # Per-class metrics
        per_class_metrics: Dict[str, Dict[str, float]] = {}
        all_class_indices = list(range(len(classes)))
        prec_per = np.asarray(precision_score(y_test, y_pred, labels=all_class_indices, average=None, zero_division=0))
        rec_per = np.asarray(recall_score(y_test, y_pred, labels=all_class_indices, average=None, zero_division=0))
        f1_per = np.asarray(f1_score(y_test, y_pred, labels=all_class_indices, average=None, zero_division=0))

        for idx, cls_name in enumerate(classes):
            per_class_metrics[cls_name] = {
                "precision": round(float(prec_per[idx]), 3),
                "recall": round(float(rec_per[idx]), 3),
                "f1_score": round(float(f1_per[idx]), 3)
            }

        # Confusion matrix
        cm = confusion_matrix(y_test, y_pred, labels=all_class_indices).tolist()

        # 5. Extract Feature Importances
        importances: Dict[str, float] = {}
        for col_name, score in zip(self.feature_columns, model.feature_importances_):
            importances[col_name] = round(float(score), 4)

        # Sort feature importances descending
        sorted_importances = dict(sorted(importances.items(), key=lambda item: item[1], reverse=True))

        metrics = {
            "accuracy": round(acc, 4),
            "macro_precision": round(macro_prec, 4),
            "macro_recall": round(macro_rec, 4),
            "macro_f1": round(macro_f1, 4),
            "per_class": per_class_metrics,
            "confusion_matrix": {
                "classes": classes,
                "matrix": cm
            }
        }

        # 6. Save Model Artifact and Metadata
        save_result = self._save_artifact(
            model=model,
            label_encoder=label_encoder,
            classes=classes,
            metrics=metrics,
            feature_importances=sorted_importances,
            dataset_version=dataset_version,
            split_metadata=split_meta
        )

        return {
            "status": "SUCCESS",
            "model_version": self.model_version,
            "model_type": "xgboost",
            "training_dataset_version": dataset_version,
            "metrics": metrics,
            "classes": classes,
            "top_features": list(sorted_importances.keys())[:5],
            "split_metadata": split_meta,
            "artifact_path": save_result["model_path"],
            "metadata_path": save_result["metadata_path"]
        }

    def _vectorize(self, records: List[TrainingDataRecord]) -> Tuple[np.ndarray, List[str]]:
        """
        Converts feature dictionaries to 2D numpy array with np.nan for missing attributes.
        """
        X_rows: List[List[float]] = []
        y_labels: List[str] = []

        for r in records:
            row: List[float] = []
            f_dict = r.features or {}
            for col in self.feature_columns:
                val = f_dict.get(col)
                if val is None:
                    row.append(np.nan)
                else:
                    try:
                        row.append(float(val))
                    except (ValueError, TypeError):
                        row.append(np.nan)
            X_rows.append(row)
            y_labels.append(r.label)

        return np.array(X_rows, dtype=np.float32), y_labels

    def _save_artifact(
        self,
        model: Any,
        label_encoder: Any,
        classes: List[str],
        metrics: Dict[str, Any],
        feature_importances: Dict[str, float],
        dataset_version: str,
        split_metadata: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Serializes model artifact and writes metadata JSON to models/<model_version>/.
        """
        version_dir = os.path.join(self.registry_dir, self.model_version)
        os.makedirs(version_dir, exist_ok=True)

        model_path = os.path.join(version_dir, "model.pkl")
        metadata_path = os.path.join(version_dir, "metadata.json")

        artifact_data = {
            "model": model,
            "label_encoder": label_encoder,
            "classes": classes,
            "feature_columns": self.feature_columns
        }

        with open(model_path, "wb") as f:
            pickle.dump(artifact_data, f)

        metadata = {
            "model_version": self.model_version,
            "model_type": "xgboost",
            "training_dataset_version": dataset_version,
            "feature_schema_version": self.feature_schema_version,
            "training_date": datetime.now(timezone.utc).isoformat(),
            "classes": classes,
            "metrics": metrics,
            "feature_columns": self.feature_columns,
            "feature_importances": feature_importances,
            "split_metadata": split_metadata,
            "library_versions": {
                "xgboost": xgb.__version__,
                "scikit-learn": sklearn.__version__,
                "numpy": np.__version__
            },
            "calibration_method": "uncalibrated_model_probability",
            "is_calibrated": False
        }

        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Model {self.model_version} successfully saved to {version_dir}")
        return {
            "model_path": model_path,
            "metadata_path": metadata_path
        }
