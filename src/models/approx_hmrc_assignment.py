#!/usr/bin/env python3
import re
import numpy as np
import pandas as pd
import gurobipy as gp
from gurobipy import GRB
from utils import load_an_instance, create_distance_dict, PROJECT_ROOT

# ---------- Helpers ----------
def norm(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"\s+", " ", s)
    s = s.replace("Portmouth", "Portsmouth")  # fix common typo
    return s.lower()

def targets_for_closure(closure: int):
    """Council targets (percent strings) for each closure scenario, in HWRC name order."""
    if closure == 0:
        # --- No closures: use provided utilization rates from table ---
        return [
            "66.63", "40.74", "89.49", "52.11", "64.22", "74.94", "54.23", "69.97", "71.02", "69.64",
            "69.89", "70.17", "74.66", "73.47", "61.00", "45.99", "39.94", "71.75", "53.81", "47.53",
            "59.24", "79.73", "32.77", "47.11", "48.36", "53.65"
        ]
    if closure == 5:
        return [
            "53.67","81.53","52.20","69.99","73.56","71.89","53.70","66.92","79.74",
            "117.00","83.31","53.91","40.86","74.94","47.11","135.78","59.24","52.72",
            "66.63","---","---","---","---","---","61.03","69.95"
        ]
    if closure == 12:
        return [
            "54.88","81.64","75.87","69.99","86.31","85.97","55.68","141.01","95.25",
            "153.67","83.31","121.23","---","---","---","---","---","---","---",
            "---","---","---","---","---","86.28","69.98"
        ]
    if closure == 17:
        return [
            "54.88","219.74","93.57","70.35","127.66","157.08","60.63","---","---",
            "---","---","---","---","---","---","---","---","---","---",
            "---","---","---","---","---","158.99","101.69"
        ]
    raise ValueError("closure must be one of {0,5,12,17}")

def forced_closed_names_for(closure: int):
    if closure == 0:
        return []  # no facilities closed
    if closure == 5:
        return ["Alresford","Bishops Waltham","Fair Oak","Hartley Wintney","Hayling Island"]
    if closure == 12:
        return [
            "Aldershot","Bordon","Casbrook","Hedge End","Marchwood","Petersfield","Somerley",
            "Alresford","Bishops Waltham","Fair Oak","Hartley Wintney","Hayling Island"
        ]
    if closure == 17:
        return [
            "Alton","Efford","Farnborough","Havant","Netley",
            "Aldershot","Bordon","Casbrook","Hedge End","Marchwood","Petersfield","Somerley",
            "Alresford","Bishops Waltham","Fair Oak","Hartley Wintney","Hayling Island"
        ]
    raise ValueError("closure must be one of {0,5,12,17}")

HWRC_ORDER = [
    "Andover","Basingstoke","Eastleigh","Gosport","Segensworth","Waterlooville","Winchester","Alton","Efford",
    "Farnborough","Havant","Netley","Aldershot","Bordon","Casbrook","Hedge End","Marchwood","Petersfield",
    "Somerley","Alresford","Bishops Waltham","Fair Oak","Hartley Wintney","Hayling Island","Southampton","Portsmouth"
]

def extract_prefix(s):
    s = str(s).strip().upper()
    m = re.match(r"^([A-Z]{1,3})", s)
    return m.group(1) if m else ""

def run_scenario(closure, users_and_facs_df, users, facs, facility_df, U, P_matrix, distance_dict, model_option):
    """Run optimization for a specific closure scenario and model option."""
    # Align basic shapes/keys
    facility_names = [re.sub(r"\s+", " ", n).strip() for n in facility_df["Facility name"].astype(str).tolist()]
    J = len(facility_names)
    user_keys = list(distance_dict.keys())          # the same order you used to build P_matrix rows
    I = len(user_keys)

    # Capacities (same order as facility_df.index)
    C = np.squeeze(facility_df['capacity'].values).astype(float)

    # Targets for this scenario → util_rate aligned to facility order
    council_raw = targets_for_closure(closure)
    assert len(HWRC_ORDER) == len(council_raw) == 26
    council_map = {norm(nm): (np.nan if v.strip() == '---' else float(v)/100.0)
                   for nm, v in zip(HWRC_ORDER, council_raw)}
    util_rate = np.array([council_map.get(norm(nm), np.nan) for nm in facility_names], dtype=float)
    target_idx = np.where(~np.isnan(util_rate))[0]

    # Build model
    m = gp.Model(f"{model_option}_closure_{closure}")
    y = m.addMVar(shape=J, vtype=GRB.BINARY, name="y")
    x = m.addMVar(shape=(I, J), vtype=GRB.BINARY, name="x")
    
    # Set upper bound based on model option
    ub = 1.0 if model_option == "UFC" else 2.0
    util_var = m.addMVar(shape=J, lb=0.0, ub=ub, vtype=GRB.CONTINUOUS, name="util_var")

    # Forced closed by name
    name_to_idx = {norm(n): j for j, n in enumerate(facility_names)}
    for nm in forced_closed_names_for(closure):
        j = name_to_idx.get(norm(nm))
        if j is not None:
            y[j].UB = 0.0
        else:
            print(f"Warning: forced-closed site not found in data (closure={closure}): {nm}")

    # Exactly J - closure open
    m.addConstr(gp.quicksum(y[j] for j in range(J)) == J - closure, name=f"open_count_{closure}")

    # Assign each user to exactly one facility
    m.addConstrs((gp.quicksum(x[i, j] for j in range(J)) == 1 for i in range(I)), name="assign_one")

    # Assign only to open
    m.addConstrs((x[i, j] <= y[j] for i in range(I) for j in range(J)), name="assign_to_open")

    # Utilization identity
    m.addConstrs(
        (gp.quicksum(U[user_keys[i]] * P_matrix[i, j] * x[i, j] for i in range(I)) == C[j] * util_var[j]
         for j in range(J)),
        name="util_identity"
    )
    
    # Set objective and constraints based on model option
    if model_option in ["UF", "UFC"]:
        # Minimize squared deviation from targets
        m.setObjective(
            gp.quicksum((util_var[j] - util_rate[j]) * (util_var[j] - util_rate[j])
                        for j in target_idx),
            GRB.MINIMIZE
        )
    elif model_option == "AMF":
        # Maximize access with band constraints
        m.setObjective(
            gp.quicksum(
                U[user_keys[i]] * P_matrix[i, j] * x[i, j]
                for i in range(I) for j in range(J)
            ),
            GRB.MAXIMIZE
        )
        
        # Add band constraints for AMF
        eps = 0.2 if closure <= 12 else 0.3
        m.addConstrs((util_var[j] >= util_rate[j] * (1 - eps) * y[j] for j in target_idx), name="band_lower")
        m.addConstrs((util_var[j] <= util_rate[j] * (1 + eps) * y[j] for j in target_idx), name="band_upper")
    else:
        raise ValueError(f"Unknown model_option: {model_option}. Must be 'UF', 'UFC', or 'AMF'.")

    # Solve
    m.Params.TimeLimit = 3600
    m.optimize()

    if m.status not in [GRB.OPTIMAL, GRB.TIME_LIMIT, GRB.SUBOPTIMAL]:
        print(f"Scenario closure={closure}: infeasible or no usable solution (status={m.status}).")
        return

    # ----- Reporting: facility table -----
    util_sol = util_var.X
    open_sol = (y.X > 0.5).astype(int)
    model_pct_full = 100.0 * np.asarray(util_sol, dtype=float)
    hcc_pct_full   = 100.0 * util_rate
    diff_full      = model_pct_full - hcc_pct_full  # NaN where no target

    def fmt_target(v): return "---" if np.isnan(v) else f"{v:.2f}%"
    def fmt_pct(v):    return f"{v:.2f}%"
    def fmt_diff(v):   return "---" if np.isnan(v) else f"{v:+.2f}%"

    df = pd.DataFrame({
        "Site":               facility_names,
        "HCC utilization":    [fmt_target(v) for v in hcc_pct_full],
        "Model utilization":  [fmt_pct(v)   for v in model_pct_full],
        "Difference":         [fmt_diff(v)  for v in diff_full],
        "Open":               pd.Series(open_sol).map({1: "Yes", 0: "No"}),
    })
    order_map = {name.lower(): i for i, name in enumerate(HWRC_ORDER)}
    df["Site_norm"] = df["Site"].str.strip().str.lower().str.replace("portmouth", "portsmouth")
    df["order"] = df["Site_norm"].map(order_map)
    df = df.sort_values("order", na_position="last").drop(columns=["Site_norm", "order"])
    out_fac_dir = PROJECT_ROOT / "own_results"
    out_fac_dir.mkdir(parents=True, exist_ok=True)
    out_fac = out_fac_dir / f"hwrc_{model_option}_closed_{closure}.csv"
    df.to_csv(out_fac, index=False)
    print(f"\nSaved facility table: {out_fac}")

    # ----- Build user→facility map from x -----
    x_sol = x.X
    assign_i, assign_j = np.where(x_sol > 0.5)
    # Map back to original user ids
    user_to_facility_model_idx = {user_keys[i]: j for i, j in zip(assign_i, assign_j)}

    # ----- A/B medians (A = Urban only in {BH,GU,RG,SP}; B = {SO,PO}) -----
    # Make assignment rows w/ distances
    rows = []
    for ui, j in user_to_facility_model_idx.items():
        j_key = facility_df.index[j]
        d = distance_dict.get(ui, {}).get(j_key)
        if d is not None:
            rows.append({"user": ui, "facility_model_idx": j, "facility_key": j_key, "distance_miles": d})
    assign_df = pd.DataFrame(rows)
    if not assign_df.empty:
        # postcode prefix (user side)
        pc_user_col = None
        for c in users_and_facs_df.columns:
            cl = c.lower()
            if ("postcode sector" in cl) or ("postcode sectors" in cl) or (cl == "postcode") or ("postcode" in cl):
                pc_user_col = c
                break
        if pc_user_col is None:
            users_and_facs_df["__pc_fallback__"] = users_and_facs_df.index
            pc_user_col = "__pc_fallback__"

        user_pc = users_and_facs_df[pc_user_col].astype(str).str.strip().str.upper()
        user_prefix = user_pc.map(extract_prefix)
        assign_df["user_prefix"] = assign_df["user"].map(user_prefix)

        # Urban flag from 'regional spatial type'
        if "regional spatial type" not in users_and_facs_df.columns:
            raise ValueError("Column 'regional spatial type' is required to restrict Group A to urban.")
        regional_type = users_and_facs_df["regional spatial type"].astype(str).str.lower().fillna("")
        def is_urban(v):
            v = v.strip().lower()
            return ("urban" in v) and not ("rural" in v)
        urban_series = regional_type.apply(is_urban)
        assign_df["is_urban"] = assign_df["user"].map(urban_series).fillna(False)

        GROUP_A_PREFIXES = {"BH","GU","RG","SP"}
        GROUP_B_PREFIXES = {"SO","PO"}

        def label_row(row):
            pref = row["user_prefix"]
            urban = bool(row["is_urban"])
            if (pref in GROUP_A_PREFIXES):
                return "A"
            if pref in GROUP_B_PREFIXES:
                return "B"
            return "Other"
        assign_df["group"] = assign_df.apply(label_row, axis=1)

        # Summary & quantiles
        med = assign_df.groupby("group")["distance_miles"].median().rename("median_miles")
        cnt = assign_df["group"].value_counts().rename("count")
        summary = pd.concat([med, cnt], axis=1).reset_index()
        A_med = med.get("A", np.nan)
        B_med = med.get("B", np.nan)
        delta = (B_med - A_med) if (pd.notna(A_med) and pd.notna(B_med)) else np.nan
        summary["delta_B_minus_A_miles"] = np.where(summary["group"] == "B", delta, np.nan)

        def q(series):
            s = series.dropna()
            return pd.Series({
                "p10": s.quantile(0.10) if not s.empty else np.nan,
                "p50": s.quantile(0.50) if not s.empty else np.nan,
                "p90": s.quantile(0.90) if not s.empty else np.nan,
            })

        # --- Group-level quantiles (A, B, Other) ---
        quantiles = assign_df.groupby("group")["distance_miles"].apply(q).reset_index()

        # --- Overall quantiles (all users together) appended after group A/B/Other ---
        overall_q = q(assign_df["distance_miles"])
        overall_q.name = "All"
        overall_df = overall_q.to_frame().T.reset_index().rename(columns={"index": "group"})

        # Append the "All" row at the end
        quantiles = pd.concat([quantiles, overall_df], ignore_index=True)

        out_dir = PROJECT_ROOT / "own_results"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_q  = out_dir / f"groupAB_quantiles_{model_option}_{closure}.csv"
        quantiles.to_csv(out_q, index=False)
        print(f"Saved quantiles table: {out_q}")
    else:
        print("No assignments with distances; A/B tables not written.")

def main():
    # -----------------------------
    # 1) Load Hampshire data / build inputs once
    # -----------------------------
    users_and_facs_df, travel_dict, users, facs = load_an_instance(
        instance_number=1,
        region="Hampshire",
        sufficient_cap=False,
    )

    facility_df = users_and_facs_df.loc[facs].copy()  # model facilities (order matters)
    population = users_and_facs_df.loc[users, 'population']
    U_full = population.to_numpy()

    # Dicts/matrices for this user/facility set
    distance_dict = create_distance_dict(users_and_facs_df, users, facs, region="Hampshire")

    # P_matrix is rows over *distance_dict.keys()* (stable order), cols over facility_df.index
    user_keys = list(distance_dict.keys())
    P_matrix = np.array([[travel_dict[i][j] for j in facility_df.index] for i in user_keys], dtype=float)

    # 2) Run all closure scenarios with all model options
    for closure in (0, 5, 12, 17):
        for model_option in ("UF", "UFC", "AMF"):
            print(f"\n=== Running scenario: {closure} closures, model={model_option} ===")
            run_scenario(closure,
                         users_and_facs_df=users_and_facs_df,
                         users=users, facs=facs,
                         facility_df=facility_df,
                         U=U_full,
                         P_matrix=P_matrix,
                         distance_dict=distance_dict,
                         model_option=model_option)

if __name__ == "__main__":
    main()