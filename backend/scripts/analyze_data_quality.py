"""
Data Quality Analysis for Ovulite Pregnancy Prediction
Identifies issues limiting model performance and suggests improvements.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import numpy as np
from ml.features import build_feature_matrix, preprocess_for_model
from ml.split import temporal_split
import json

def analyze_data_quality():
    """Comprehensive data quality analysis."""
    
    print("=" * 80)
    print("OVULITE DATA QUALITY ANALYSIS")
    print("=" * 80)
    
    # Load data
    print("\n[1/8] Loading feature matrix...")
    df = build_feature_matrix(None)
    print(f"Total samples: {len(df)}")
    
    # Target analysis
    print("\n[2/8] Analyzing target variable (pregnancy_outcome)...")
    target_col = 'pregnancy_outcome'
    if target_col in df.columns:
        target_counts = df[target_col].value_counts()
        target_pct = df[target_col].value_counts(normalize=True) * 100
        print(f"Target distribution:")
        for val, count in target_counts.items():
            print(f"  {val}: {count} ({target_pct[val]:.1f}%)")
        
        # Check for extreme imbalance
        minority_pct = min(target_pct.values)
        if minority_pct < 10:
            print(f"⚠️  SEVERE CLASS IMBALANCE: Minority class is only {minority_pct:.1f}%")
            print("   → Consider SMOTE, class weights, or stratified sampling")
    else:
        print(f"⚠️  Target variable '{target_col}' not found!")
        print(f"Available columns: {df.columns.tolist()}")
        return
    
    # Missing values analysis
    print("\n[3/8] Analyzing missing values...")
    missing = df.isnull().sum()
    missing_pct = (missing / len(df) * 100).round(1)
    missing_df = pd.DataFrame({
        'missing_count': missing,
        'missing_pct': missing_pct
    }).sort_values('missing_pct', ascending=False)
    
    high_missing = missing_df[missing_df['missing_pct'] > 50]
    if len(high_missing) > 0:
        print(f"⚠️  {len(high_missing)} features with >50% missing:")
        for col, row in high_missing.head(10).iterrows():
            print(f"  {col}: {row['missing_pct']:.1f}% missing")
    else:
        print("✓ No features with >50% missing values")
    
    # Feature types
    print("\n[4/8] Analyzing feature types...")
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if target_col in numeric_cols:
        numeric_cols.remove(target_col)
    categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
    
    print(f"Numeric features: {len(numeric_cols)}")
    print(f"Categorical features: {len(categorical_cols)}")
    
    # Cardinality check for categorical
    high_cardinality = []
    for col in categorical_cols:
        n_unique = df[col].nunique()
        if n_unique > 50:
            high_cardinality.append((col, n_unique))
    
    if high_cardinality:
        print(f"⚠️  {len(high_cardinality)} high-cardinality categorical features:")
        for col, n in sorted(high_cardinality, key=lambda x: x[1], reverse=True)[:5]:
            print(f"  {col}: {n} unique values")
        print("   → May cause overfitting or encoding issues")
    
    # Constant/near-constant features
    print("\n[5/8] Checking for low-variance features...")
    low_var_features = []
    for col in numeric_cols:
        if df[col].nunique() == 1:
            low_var_features.append((col, 'constant'))
        elif df[col].nunique() == 2 and df[col].value_counts(normalize=True).max() > 0.99:
            low_var_features.append((col, 'near-constant'))
    
    if low_var_features:
        print(f"⚠️  {len(low_var_features)} low-variance features found:")
        for col, var_type in low_var_features[:10]:
            print(f"  {col}: {var_type}")
        print("   → These provide no predictive signal")
    else:
        print("✓ No constant features detected")
    
    # Correlation with target
    print("\n[6/8] Computing correlations with target...")
    correlations = []
    for col in numeric_cols:
        if df[col].notna().sum() > 10:  # Need at least 10 non-null values
            corr = df[[col, target_col]].dropna().corr().iloc[0, 1]
            if not np.isnan(corr):
                correlations.append((col, abs(corr), corr))
    
    correlations.sort(key=lambda x: x[1], reverse=True)
    
    print(f"Top 10 features by absolute correlation with pregnancy:")
    if correlations:
        for col, abs_corr, corr in correlations[:10]:
            direction = "+" if corr > 0 else "-"
            print(f"  {col}: {direction}{abs_corr:.3f}")
        
        max_corr = correlations[0][1]
        if max_corr < 0.1:
            print(f"\n⚠️  CRITICAL: Strongest correlation is only {max_corr:.3f}")
            print("   → Features have very weak predictive signal")
            print("   → Need better features or more informative data")
    else:
        print("⚠️  No valid correlations computed!")
    
    # Multicollinearity check
    print("\n[7/8] Checking for multicollinearity...")
    if len(numeric_cols) > 1:
        # Sample numeric data
        numeric_data = df[numeric_cols].select_dtypes(include=[np.number])
        numeric_data = numeric_data.dropna(axis=1, how='all')
        
        if numeric_data.shape[1] > 1:
            corr_matrix = numeric_data.corr().abs()
            # Get upper triangle
            upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
            high_corr_pairs = []
            for col in upper.columns:
                high_corr = upper[col][upper[col] > 0.9].index.tolist()
                for other_col in high_corr:
                    high_corr_pairs.append((col, other_col, upper[col][other_col]))
            
            if high_corr_pairs:
                print(f"⚠️  {len(high_corr_pairs)} feature pairs with correlation >0.9:")
                for col1, col2, corr in high_corr_pairs[:5]:
                    print(f"  {col1} <-> {col2}: {corr:.3f}")
                print("   → Consider removing redundant features")
            else:
                print("✓ No severe multicollinearity detected")
    
    # Data size check
    print("\n[8/8] Checking data sufficiency...")
    train_df, test_df = temporal_split(df)
    print(f"Training samples: {len(train_df)}")
    print(f"Holdout samples: {len(test_df)}")
    
    X_train, y_train, feature_names, _ = preprocess_for_model(train_df, fit=True)
    print(f"Features after preprocessing: {len(feature_names)}")
    
    samples_per_feature = len(train_df) / len(feature_names)
    print(f"Samples per feature: {samples_per_feature:.1f}")
    
    if samples_per_feature < 10:
        print(f"⚠️  CRITICAL: Only {samples_per_feature:.1f} samples per feature")
        print("   → High risk of overfitting")
        print("   → Need more data or fewer features")
    elif samples_per_feature < 20:
        print(f"⚠️  WARNING: Only {samples_per_feature:.1f} samples per feature")
        print("   → May struggle to learn patterns")
    
    # Summary and recommendations
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    
    recommendations = []
    
    if minority_pct < 15:
        recommendations.append("1. Handle class imbalance using SMOTE or class weights")
    
    if len(high_missing) > 0:
        recommendations.append("2. Address high missing value rates (imputation or removal)")
    
    if correlations and correlations[0][1] < 0.15:
        recommendations.append("3. CRITICAL: Create better features with domain knowledge")
        recommendations.append("   - Ratios (e.g., embryo quality / donor age)")
        recommendations.append("   - Interactions (e.g., protocol × timing)")
        recommendations.append("   - Temporal features (season, trends)")
    
    if samples_per_feature < 20:
        recommendations.append("4. Either collect more data OR reduce feature count")
    
    if len(high_cardinality) > 0:
        recommendations.append("5. Group high-cardinality categories or use target encoding")
    
    if not recommendations:
        recommendations.append("Data quality looks reasonable.")
        recommendations.append("Consider advanced techniques: ensemble methods, hyperparameter tuning")
    
    for rec in recommendations:
        print(rec)
    
    # Generate report file
    report = {
        "total_samples": len(df),
        "train_samples": len(train_df),
        "test_samples": len(test_df),
        "target_distribution": target_counts.to_dict() if target_col in df.columns else {},
        "num_features_raw": len(numeric_cols) + len(categorical_cols),
        "num_features_processed": len(feature_names),
        "samples_per_feature": float(samples_per_feature),
        "top_correlations": [(col, float(corr)) for col, _, corr in correlations[:10]],
        "high_missing_features": high_missing.index.tolist(),
        "low_variance_features": [col for col, _ in low_var_features],
        "recommendations": recommendations
    }
    
    report_path = PROJECT_ROOT / "ml" / "artifacts" / "data_quality_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n✓ Report saved to: {report_path}")
    print("=" * 80)

if __name__ == "__main__":
    analyze_data_quality()
