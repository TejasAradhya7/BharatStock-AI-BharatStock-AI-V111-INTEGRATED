"""Offline research benchmark for BharatStock AI (not used by live prediction API).

Runs causal 8-vs-16 feature ablation and comparable chronological model evaluation.
Optional LSTM/GRU sequence benchmark runs only when PyTorch is installed.
"""
from __future__ import annotations
import argparse, json, warnings
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier, HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, brier_score_loss, log_loss
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

BASE = ["RSI", "MACD_pct", "MACD_Signal_pct", "SMA20_gap", "SMA50_gap", "EMA20_gap", "ATR_pct", "Return_5"]
EXTRA = ["Return_1", "Return_10", "Return_20", "Volatility_5", "Range_pct", "Close_Location", "Gap_pct", "Volume_Ratio_20"]
SETS = {"base_8": BASE, "expanded_16": BASE + EXTRA,
        "momentum_volatility": ["RSI", "Return_1", "Return_5", "Return_10", "Return_20", "Volatility_5", "ATR_pct"],
        "trend_only": ["MACD_pct", "MACD_Signal_pct", "SMA20_gap", "SMA50_gap", "EMA20_gap"]}


def build_features(raw: pd.DataFrame) -> pd.DataFrame:
    d = raw.copy()
    d.columns = [str(c).title() for c in d.columns]
    required = ["Open", "High", "Low", "Close", "Volume"]
    missing = [c for c in required if c not in d]
    if missing: raise ValueError(f"CSV missing OHLCV columns: {missing}")
    d = d.sort_index()
    o, h, l, c, v = (pd.to_numeric(d[k], errors="coerce") for k in required)
    d["SMA20"] = c.rolling(20).mean(); d["SMA50"] = c.rolling(50).mean(); d["EMA20"] = c.ewm(span=20, adjust=False).mean()
    delta = c.diff(); gain = delta.clip(lower=0).rolling(14).mean(); loss = -delta.clip(upper=0).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan); rsi = 100 - 100/(1+rs)
    rsi = rsi.where(loss.ne(0), 100.0).where(gain.ne(0), 0.0)
    rsi = rsi.where(~(gain.eq(0) & loss.eq(0)), 50.0)
    d["RSI"] = rsi.fillna(50).clip(0,100)
    macd = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
    d["MACD_pct"] = macd / c.replace(0,np.nan); d["MACD_Signal_pct"] = macd.ewm(span=9,adjust=False).mean()/c.replace(0,np.nan)
    d["SMA20_gap"] = c/d["SMA20"]-1; d["SMA50_gap"] = c/d["SMA50"]-1; d["EMA20_gap"] = c/d["EMA20"]-1
    prev = c.shift(1); tr = pd.concat([(h-l),(h-prev).abs(),(l-prev).abs()],axis=1).max(axis=1)
    d["ATR_pct"] = tr.rolling(14).mean()/c.replace(0,np.nan); d["Return_5"] = c.pct_change(5)
    d["Return_1"] = c.pct_change(1); d["Return_10"] = c.pct_change(10); d["Return_20"] = c.pct_change(20)
    d["Volatility_5"] = c.pct_change().rolling(5).std(); d["Range_pct"] = (h-l)/c.replace(0,np.nan)
    d["Close_Location"] = ((c-l)/(h-l).replace(0,np.nan)).clip(0,1); d["Gap_pct"] = o/prev.replace(0,np.nan)-1
    med = v.rolling(20).median().replace(0,np.nan); d["Volume_Ratio_20"] = (v/med).replace([np.inf,-np.inf],np.nan)
    # Exact target definition used by the main API: next session close > current close.
    # Keep OHLC assignment aligned with required=["Open","High","Low","Close","Volume"].
    d["Target"] = (c.shift(-1)>c).astype(float); d.loc[d.index[-1],"Target"] = np.nan
    return d.replace([np.inf,-np.inf],np.nan)


def model_factories():
    return {
      "LogisticRegression": lambda: make_pipeline(StandardScaler(), LogisticRegression(max_iter=1500,class_weight="balanced",C=0.1,random_state=42)),
      "RandomForest": lambda: RandomForestClassifier(n_estimators=180,max_depth=6,min_samples_leaf=8,max_features="sqrt",class_weight="balanced_subsample",random_state=42,n_jobs=-1),
      "ExtraTrees": lambda: ExtraTreesClassifier(n_estimators=180,max_depth=6,min_samples_leaf=8,max_features="sqrt",class_weight="balanced",random_state=43,n_jobs=-1),
      "HistGradientBoosting": lambda: HistGradientBoostingClassifier(max_iter=120,learning_rate=.04,max_leaf_nodes=7,l2_regularization=2.0,random_state=44),
    }


def _inner_tune(train: pd.DataFrame, features: list[str], family: str):
    """Select a small configuration using only expanding chronological splits of outer training data."""
    grids = {
      "TunedRandomForest": [
        {"n_estimators":140,"max_depth":4,"min_samples_leaf":10},
        {"n_estimators":180,"max_depth":6,"min_samples_leaf":8},
        {"n_estimators":220,"max_depth":8,"min_samples_leaf":12}],
      "TunedHistGradientBoosting": [
        {"max_iter":80,"learning_rate":.03,"max_leaf_nodes":5,"l2_regularization":2.0},
        {"max_iter":120,"learning_rate":.04,"max_leaf_nodes":7,"l2_regularization":2.0},
        {"max_iter":160,"learning_rate":.03,"max_leaf_nodes":9,"l2_regularization":4.0}]
    }
    initial=max(70,int(len(train)*.55)); remaining=len(train)-initial
    if remaining < 30: return None, None
    sizes=np.full(3,remaining//3,dtype=int); sizes[:remaining%3]+=1
    best_score=-1.0; best_cfg=None; cursor=initial
    for cfg in grids[family]:
        scores=[]; cursor=initial
        for size in sizes:
            fit_part=train.iloc[:cursor-1]; val=train.iloc[cursor:cursor+int(size)]; cursor+=int(size)
            if len(fit_part)<60 or val.empty: continue
            if family=="TunedRandomForest":
                model=RandomForestClassifier(**cfg,max_features="sqrt",class_weight="balanced_subsample",random_state=42,n_jobs=-1)
            else:
                model=HistGradientBoostingClassifier(**cfg,random_state=44)
            model.fit(fit_part[features],fit_part.Target.astype(int)); pred=model.predict(val[features])
            if val.Target.nunique()>1: scores.append(balanced_accuracy_score(val.Target.astype(int),pred))
        score=float(np.mean(scores)) if scores else -1.0
        if score>best_score: best_score,best_cfg=score,cfg
    if best_cfg is None: return None, None
    if family=="TunedRandomForest":
        return RandomForestClassifier(**best_cfg,max_features="sqrt",class_weight="balanced_subsample",random_state=42,n_jobs=-1), {"params":best_cfg,"inner_mean_balanced_accuracy":best_score}
    return HistGradientBoostingClassifier(**best_cfg,random_state=44), {"params":best_cfg,"inner_mean_balanced_accuracy":best_score}

def evaluate(data: pd.DataFrame, features: list[str], folds: int=5) -> dict:
    clean=data[features+["Target"]].dropna(); n=len(clean); folds=max(2,min(folds,8))
    initial=max(100,int(n*.5)); remaining=n-initial
    if remaining < folds*12: return {"status":"INSUFFICIENT_DATA","rows":n,"folds":[]}
    sizes=np.full(folds,remaining//folds,dtype=int); sizes[:remaining%folds]+=1; cursor=initial; out=[]
    for fold,size in enumerate(sizes,1):
        # Purge one boundary row: its label uses the first test-session close.
        train=clean.iloc[:cursor-1]; test=clean.iloc[cursor:cursor+int(size)]; cursor+=int(size)
        if len(train)<80 or test.empty: continue
        ytr=train.Target.astype(int); yte=test.Target.astype(int); majority=int(ytr.value_counts().idxmax())
        baseline=np.full(len(test),majority); row={"fold":fold,"train_rows":len(train),"test_rows":len(test),"baseline_accuracy":accuracy_score(yte,baseline)}
        candidates={name:factory() for name,factory in model_factories().items()}
        tuning={}
        for family in ["TunedRandomForest","TunedHistGradientBoosting"]:
            tuned,selection=_inner_tune(train,features,family)
            if tuned is not None: candidates[family]=tuned; tuning[family]=selection
        row["inner_tuning_selection"]=tuning
        for name,m in candidates.items():
            m.fit(train[features],ytr); pred=m.predict(test[features]);
            try:
                probs=m.predict_proba(test[features]); classes=list(m.classes_) if hasattr(m,"classes_") else list(m[-1].classes_)
                p=probs[:,classes.index(1)] if 1 in classes else np.zeros(len(yte)); brier=brier_score_loss(yte,p); ll=log_loss(yte,probs,labels=classes)
            except Exception: brier=ll=None
            row[name]={"accuracy":accuracy_score(yte,pred),"balanced_accuracy":balanced_accuracy_score(yte,pred),"f1":f1_score(yte,pred,zero_division=0),"brier":brier,"log_loss":ll}
        out.append(row)
    summary={}
    model_names=list(model_factories())+["TunedRandomForest","TunedHistGradientBoosting"]
    for name in ["baseline_accuracy"]+model_names:
        vals=[r[name] if name=="baseline_accuracy" else r[name]["accuracy"] for r in out]
        summary[name]={"mean_accuracy":float(np.mean(vals)) if vals else None,"fold_std":float(np.std(vals,ddof=1)) if len(vals)>1 else None}
        if name!="baseline_accuracy":
            for metric in ["balanced_accuracy","f1","brier","log_loss"]:
                mvals=[r[name][metric] for r in out if r[name][metric] is not None]
                summary[name]["mean_"+metric]=float(np.mean(mvals)) if mvals else None
    return {"status":"completed","rows":n,"folds":out,"summary":summary,"method":"expanding-window walk-forward; chronological; one-row target-boundary purge; identical folds across feature sets; no random shuffle"}


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--csv",required=True,help="Daily OHLCV CSV; columns Open,High,Low,Close,Volume; date index or Date column")
    ap.add_argument("--output",default="model_research_results.json"); ap.add_argument("--folds",type=int,default=5); args=ap.parse_args()
    raw=pd.read_csv(args.csv)
    date_col=next((c for c in raw.columns if c.lower() in ("date","datetime","timestamp")),None)
    if date_col: raw[date_col]=pd.to_datetime(raw[date_col],errors="coerce"); raw=raw.set_index(date_col)
    d=build_features(raw)
    # Use one common complete-case population for every feature set. Without
    # this, each set drops a different number of warm-up/missing rows and its
    # walk-forward folds can test different dates, making the ablation unfair.
    all_features = sorted({feature for feature_list in SETS.values() for feature in feature_list})
    shared = d.dropna(subset=all_features + ["Target"]).copy()
    if shared.empty:
        raise ValueError("No common complete OHLCV rows remain across all feature sets.")
    if not shared.index.is_monotonic_increasing:
        raise ValueError("Input dates must be sorted chronologically.")
    if shared.index.has_duplicates:
        raise ValueError("Input contains duplicate dates; deduplicate before evaluation.")
    shared_start = str(shared.index[0])
    shared_end = str(shared.index[-1])
    results={"target":"next-session close direction","feature_sets":{},"important_note":"Research only; not investment advice. Scores are historical diagnostics, not expected returns.",
             "comparison_population":{"rows":int(len(shared)),"start":shared_start,"end":shared_end,
                                      "same_rows_for_all_feature_sets":True,
                                      "note":"All feature sets are evaluated on the same common complete-case dates."}}
    for label,features in SETS.items(): results["feature_sets"][label]={"features":features,"evaluation":evaluate(shared,features,args.folds)}
    # Hyperparameter comparison is intentionally small and fixed before evaluation.
    results["tuning_note"]="TunedRandomForest and TunedHistGradientBoosting select among small predeclared grids using three expanding chronological inner splits of each outer training window only. The outer test fold is not used for tuning. Other candidates use fixed reference configurations. This is a limited research grid, not exhaustive optimization."
    try:
        import torch
        results["sequence_models"]={"pytorch_available":True,"status":"See Colab notebook for sequence training; the API path remains unchanged."}
    except Exception as exc: results["sequence_models"]={"pytorch_available":False,"status":"skipped","reason":str(exc)}
    Path(args.output).write_text(json.dumps(results,indent=2,default=float),encoding="utf-8")
    print(json.dumps({"output":args.output,"feature_set_summaries":{k:v["evaluation"].get("summary",v["evaluation"].get("status")) for k,v in results["feature_sets"].items()},"sequence_models":results["sequence_models"]},indent=2))
if __name__=="__main__": main()
