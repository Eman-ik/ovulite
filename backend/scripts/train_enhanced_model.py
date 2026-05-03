"""
Enhanced Training Pipeline v2
Addresses data quality issues to improve from 0.50 to target 0.87 ROC-AUC
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import argparse
import json
from datetime import datetime

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    roc_auc_score,
    average_precision_score,
    f1_score,
    brier_score_loss,
    confusion_matrix,
    classification_report,
    roc_curve
)
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.preprocessing import StandardScaler
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline

from ml.config import TARGET_COL
from ml.features_v2 import build_enhanced_feature_matrix, select_top_features
from ml.split import temporal_split


def train_enhanced_model(version="v2_enhanced"):
    """Train enhanced models with improved features and techniques."""
    
    print("=" * 80)
    print(f"ENHANCED TRAINING PIPELINE - {version}")
    print("=" * 80)
    
    # ═══════════════════════════════════════════════════════════
    # STEP 1: Load enhanced features
    # ═══════════════════════════════════════════════════════════
    print("\n[1/6] Building enhanced feature matrix...")
    df = build_enhanced_feature_matrix(None)
    print(f"Loaded {len(df)} samples")
    
    # ═══════════════════════════════════════════════════════════
    # STEP 2: Temporal split
    # ═══════════════════════════════════════════════════════════
    print("\n[2/6] Performing temporal split...")
    train_df, test_df = temporal_split(df)
    print(f"Train: {len(train_df)} | Test: {len(test_df)}")
    
    # Check class distribution
    train_dist = train_df[TARGET_COL].value_counts()
    print(f"Training target distribution: {dict(train_dist)}")
    
    # ═══════════════════════════════════════════════════════════
    # STEP 3: Feature selection (reduce overfitting)
    # ═══════════════════════════════════════════════════════════
    print("\n[3/6] Selecting top features...")
    selected_features = select_top_features(train_df, TARGET_COL, max_features=12)
    
    # Prepare feature matrices
    X_train = train_df[selected_features].fillna(train_df[selected_features].median())
    y_train = train_df[TARGET_COL]
    X_test = test_df[selected_features].fillna(train_df[selected_features].median())
    y_test = test_df[TARGET_COL]
    
    print(f"Feature matrix: {X_train.shape}")
    print(f"Samples per feature: {len(X_train) / X_train.shape[1]:.1f}")
    
    # ═══════════════════════════════════════════════════════════
    # STEP 4: Train models with SMOTE + regularization
    # ═══════════════════════════════════════════════════════════
    print("\n[4/6] Training models with SMOTE and regularization...")
    
    models = {}
    results = {}
    
    # Model 1: Logistic Regression with strong L2 regularization
    print("\n  Training Logistic Regression (L2)...")
    lr_pipeline = ImbPipeline([
        ('scaler', StandardScaler()),
        ('smote', SMOTE(random_state=42, k_neighbors=3)),  # k_neighbors=3 for small dataset
        ('classifier', LogisticRegression(
            C=0.1,  # Strong regularization
            class_weight='balanced',
            max_iter=1000,
            random_state=42
        ))
    ])
    lr_pipeline.fit(X_train, y_train)
    models['LogisticRegression_L2'] = lr_pipeline
    
    # Model 2: Random Forest (handles non-linear relationships)
    print("  Training Random Forest...")
    rf_pipeline = ImbPipeline([
        ('scaler', StandardScaler()),
        ('smote', SMOTE(random_state=42, k_neighbors=3)),
        ('classifier', RandomForestClassifier(
            n_estimators=100,
            max_depth=4,  # Shallow trees to prevent overfitting
            min_samples_split=20,
            min_samples_leaf=10,
            class_weight='balanced',
            random_state=42
        ))
    ])
    rf_pipeline.fit(X_train, y_train)
    models['RandomForest'] = rf_pipeline
    
    # Model 3: Gradient Boosting (often best for tabular data)
    print("  Training Gradient Boosting...")
    gb_pipeline = ImbPipeline([
        ('scaler', StandardScaler()),
        ('smote', SMOTE(random_state=42, k_neighbors=3)),
        ('classifier', GradientBoostingClassifier(
            n_estimators=50,
            max_depth=3,
            learning_rate=0.05,  # Slow learning
            subsample=0.8,  # Prevent overfitting
            random_state=42
        ))
    ])
    gb_pipeline.fit(X_train, y_train)
    models['GradientBoosting'] = gb_pipeline
    
    # ═══════════════════════════════════════════════════════════
    # STEP 5: Cross-validation on training set
    # ═══════════════════════════════════════════════════════════
    print("\n[5/6] Cross-validation scores...")
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    
    for name, pipeline in models.items():
        cv_scores = cross_val_score(pipeline, X_train, y_train, cv=cv, scoring='roc_auc')
        print(f"  {name}: CV ROC-AUC = {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")
    
    # ═══════════════════════════════════════════════════════════
    # STEP 6: Evaluate on holdout test set
    # ═══════════════════════════════════════════════════════════
    print("\n[6/6] Holdout test set evaluation...")
    
    for name, pipeline in models.items():
        y_pred = pipeline.predict(X_test)
        y_proba = pipeline.predict_proba(X_test)[:, 1]
        
        results[name] = {
            'accuracy': float(accuracy_score(y_test, y_pred)),
            'roc_auc': float(roc_auc_score(y_test, y_proba)),
            'pr_auc': float(average_precision_score(y_test, y_proba)),
            'f1': float(f1_score(y_test, y_pred)),
            'brier': float(brier_score_loss(y_test, y_proba))
        }
        
        cm = confusion_matrix(y_test, y_pred)
        results[name]['confusion_matrix'] = cm.tolist()
        
        print(f"\n{name}:")
        print(f"  Accuracy:  {results[name]['accuracy']:.4f}")
        print(f"  ROC-AUC:   {results[name]['roc_auc']:.4f}")
        print(f"  PR-AUC:    {results[name]['pr_auc']:.4f}")
        print(f"  F1 Score:  {results[name]['f1']:.4f}")
        print(f"  Confusion Matrix:")
        print(f"    TN={cm[0,0]} FP={cm[0,1]}")
        print(f"    FN={cm[1,0]} TP={cm[1,1]}")
    
    # Select best model by ROC-AUC
    best_model_name = max(results.keys(), key=lambda k: results[k]['roc_auc'])
    best_roc_auc = results[best_model_name]['roc_auc']
    print(f"\n🏆 Best model: {best_model_name} (ROC-AUC: {best_roc_auc:.4f})")
    
    # ═══════════════════════════════════════════════════════════
    # Save artifacts
    # ═══════════════════════════════════════════════════════════
    artifact_dir = PROJECT_ROOT / "ml" / "artifacts" / version
    artifact_dir.mkdir(parents=True, exist_ok=True)
    
    # Save models
    for name, pipeline in models.items():
        model_path = artifact_dir / f"{name.lower()}_model.joblib"
        joblib.dump(pipeline, model_path)
        print(f"✓ Saved: {model_path}")
    
    # Save metadata
    metadata = {
        'version': version,
        'timestamp': datetime.now().isoformat(),
        'train_samples': len(train_df),
        'test_samples': len(test_df),
        'features': selected_features,
        'num_features': len(selected_features),
        'target_col': TARGET_COL,
        'model_scores': results,
        'best_model': best_model_name,
        'techniques_used': [
            'Enhanced domain-specific features',
            'Feature selection (top 12)',
            'SMOTE oversampling',
            'Strong L2 regularization',
            'Ensemble methods',
            'Cross-validation'
        ]
    }
    
    metadata_path = artifact_dir / "metadata.json"
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"✓ Saved: {metadata_path}")
    
    # Generate ROC curves
    try:
        import matplotlib.pyplot as plt
        
        plt.figure(figsize=(10, 6))
        for name, pipeline in models.items():
            y_proba = pipeline.predict_proba(X_test)[:, 1]
            fpr, tpr, _ = roc_curve(y_test, y_proba)
            auc = results[name]['roc_auc']
            plt.plot(fpr, tpr, label=f"{name} (AUC={auc:.3f})", linewidth=2)
        
        plt.plot([0, 1], [0, 1], 'k--', alpha=0.5, label='Random (AUC=0.500)')
        plt.xlabel('False Positive Rate', fontsize=12)
        plt.ylabel('True Positive Rate', fontsize=12)
        plt.title(f'Enhanced Model ROC Curves - {version}', fontsize=14)
        plt.legend(loc='lower right')
        plt.grid(alpha=0.3)
        plt.tight_layout()
        
        roc_path = artifact_dir / "roc_curves.png"
        plt.savefig(roc_path, dpi=150, bbox_inches='tight')
        print(f"✓ Saved: {roc_path}")
        plt.close()
    except Exception as e:
        print(f"⚠️  Could not generate ROC curves: {e}")
    
    print("\n" + "=" * 80)
    print(f"TRAINING COMPLETE - Artifacts saved to: {artifact_dir}")
    print("=" * 80)
    
    return results, best_model_name


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', default='v2_enhanced', help='Artifact version name')
    args = parser.parse_args()
    
    results, best_model = train_enhanced_model(args.version)
    
    best_auc = results[best_model]['roc_auc']
    if best_auc >= 0.87:
        print(f"\n✅ SUCCESS: Achieved target {best_auc:.4f} ≥ 0.87 ROC-AUC!")
    else:
        gap = 0.87 - best_auc
        print(f"\n⚠️  Gap remaining: {gap:.4f} to reach 0.87 target")
        print("   Next steps: More data collection or additional feature engineering")
